import asyncio
import inspect
import multiprocessing as mp
import pickle
import queue
import traceback as tb
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Generic, TypeVar

import anyio.to_thread

T = TypeVar("T")
from fastapi import FastAPI, WebSocket

from .lifespan import get_manager, get_process_pool
from .queue import _RpcQueue
from .types import (
    CallMessage,
    ErrorMessage,
    ExitMessage,
    Message,
    QueuePutMessage,
    QueueRef,
    ResponseTypeMessage,
    ReturnMessage,
    YieldMessage,
)


@dataclass
class _ProcessYieldResult:
    """プロセスからのyield結果"""

    value: Any


@dataclass
class _ProcessReturnResult:
    """プロセスからのreturn結果"""

    value: Any


@dataclass
class _ProcessExitResult:
    pass


@dataclass
class _ProcessErrorResult:
    """プロセスからのエラー結果"""

    error_type: str
    error_message: str
    traceback: str


_ProcessResult = _ProcessYieldResult | _ProcessReturnResult | _ProcessErrorResult | _ProcessExitResult


class _QueueProxy(Generic[T]):
    """multiprocessing.Queueをqueue.Queueインターフェースでラップする"""

    def __init__(self, mq: Any):  # mp.Queue type
        self._mq = mq

    def get(self, block: bool = True, timeout: float | None = None) -> T:
        return self._mq.get(block=block, timeout=timeout)  # type: ignore[no-any-return]

    def put(self, item: T, block: bool = True, timeout: float | None = None) -> None:
        self._mq.put(item, block=block, timeout=timeout)


async def _cancel_task(task: asyncio.Task) -> None:
    """
    非同期タスクをキャンセルし、完了を待つ

    Args:
        task: キャンセルするタスク
    """
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass
    except Exception:  # pragma: no cover
        pass


async def create_rpc_endpoint(app: FastAPI, ws: WebSocket) -> None:
    """
    WebSocketエンドポイントでRPCリクエストを処理する

    Args:
        app: FastAPIアプリケーション
        ws: WebSocketコネクション
    """
    await ws.accept()

    try:
        # CallMessageを受信
        data = await ws.receive_bytes()
        message: Message = pickle.loads(data)

        if not isinstance(message, CallMessage):  # pragma: no branch
            raise ValueError(f"Expected CallMessage, got {type(message).__name__}")

        call_msg = message
        func = call_msg.func
        args = call_msg.args
        kwargs = call_msg.kwargs

        # managerを取得
        manager = get_manager(app)

        # argsとkwargsからRpcQueueを抽出してQueueRefに置き換え
        queue_map: dict[int, "queue.Queue[Any]"] = {}

        processed_args = [_convert_rpc_queue_to_ref(arg, manager, queue_map) for arg in args]
        processed_kwargs = {k: _convert_rpc_queue_to_ref(v, manager, queue_map) for k, v in kwargs.items()}

        # メッセージディスパッチャーを起動
        dispatcher_task = asyncio.create_task(_message_dispatcher(ws, queue_map))

        # 結果を受信するキュー
        result_queue: "queue.Queue[_ProcessResult]" = manager.Queue()  # type: ignore[attr-defined]

        # プロセスプールで関数を実行
        pool = get_process_pool(app)

        # 最初にResponseTypeを送信
        is_generator = inspect.isgeneratorfunction(func)
        response_type_msg = ResponseTypeMessage(is_generator=is_generator)
        await ws.send_bytes(pickle.dumps(response_type_msg))

        # 関数をプロセスで実行（非同期で実行、結果はresult_queueに送信される）
        pool.submit(
            _execute_function_in_process,
            func,
            tuple(processed_args),
            processed_kwargs,
            queue_map,
            result_queue,
        )

        # result_queueから結果を受信してクライアントに送信
        try:
            while True:
                # anyio.to_thread.run_syncを使って非ブロッキングで結果を取得
                result: _ProcessResult = await anyio.to_thread.run_sync(result_queue.get)

                match result:
                    case _ProcessYieldResult(value=value):
                        yield_msg = YieldMessage(value=value)
                        await ws.send_bytes(pickle.dumps(yield_msg))
                    case _ProcessReturnResult(value=value):
                        return_msg = ReturnMessage(value=value)
                        await ws.send_bytes(pickle.dumps(return_msg))
                    case _ProcessErrorResult(error_type=error_type, error_message=error_message, traceback=traceback):
                        error_response = ErrorMessage(
                            error_type=error_type,
                            error_message=error_message,
                            traceback=traceback,
                        )
                        await ws.send_bytes(pickle.dumps(error_response))
                    case _ProcessExitResult():
                        break
        except Exception:  # pragma: no cover
            # ディスパッチャーを早めにキャンセル
            dispatcher_task.cancel()
            raise
        finally:
            # ReturnやErrorの後も必ずExitを送信
            try:
                await ws.send_bytes(pickle.dumps(ExitMessage()))
            except Exception:  # pragma: no cover
                pass

            # ディスパッチャーをキャンセル
            await _cancel_task(dispatcher_task)

    except Exception as e:
        # エラーをクライアントに送信
        error_msg = ErrorMessage(
            error_type=type(e).__name__,
            error_message=str(e),
            traceback=tb.format_exc(),
        )
        try:
            await ws.send_bytes(pickle.dumps(error_msg))
            # Errorの後も必ずExitを送信
            await ws.send_bytes(pickle.dumps(ExitMessage()))
        except Exception:  # pragma: no cover
            pass

    finally:
        try:
            await ws.close()
        except RuntimeError:  # pragma: no cover
            # WebSocketが既に閉じられている場合
            pass


def _replace_queue_refs_with_proxies(
    args: tuple[Any, ...],
    kwargs: dict[str, Any],
    queue_map: dict[int, "queue.Queue[Any]"],
) -> tuple[list[Any], dict[str, Any]]:
    """
    argsとkwargsの中のQueueRefをqueue.Queueに置き換え

    Args:
        args: 位置引数
        kwargs: キーワード引数
        queue_map: キューIDとqueueのマッピング

    Returns:
        処理済みのargs, kwargs
    """

    def replace_ref(value: Any) -> Any:
        return _QueueProxy(queue_map[value.queue_id]) if isinstance(value, QueueRef) else value

    processed_args = [replace_ref(arg) for arg in args]
    processed_kwargs = {k: replace_ref(v) for k, v in kwargs.items()}

    return processed_args, processed_kwargs


def _execute_function_in_process(
    func: Callable[..., Any],
    args: tuple[Any, ...],
    kwargs: dict[str, Any],
    queue_map: dict[int, "queue.Queue[Any]"],
    result_queue: "queue.Queue[_ProcessResult]",
) -> None:
    """
    プロセス内で関数を実行し、結果をresult_queueに送信する

    Args:
        func: 実行する関数
        args: 位置引数 (QueueRefはqueue.Queueに置き換えられる)
        kwargs: キーワード引数 (QueueRefはqueue.Queueに置き換えられる)
        queue_map: キューIDとmultiprocessing.Queueのマッピング
        result_queue: 結果を送信するmultiprocessing.Queue
    """
    try:
        # 非同期関数はサポートしない
        if inspect.iscoroutinefunction(func):  # pragma: no branch
            result_queue.put(
                _ProcessErrorResult(
                    error_type="TypeError",
                    error_message="Async functions are not supported in RPC",
                    traceback="",
                )
            )
            return

        # argsとkwargsの中のキューIDインデックスをqueue.Queueに置き換え
        processed_args, processed_kwargs = _replace_queue_refs_with_proxies(args, kwargs, queue_map)

        result = func(*processed_args, **processed_kwargs)

        # ジェネレータの場合
        if inspect.isgenerator(result):
            for item in result:
                result_queue.put(_ProcessYieldResult(value=item))
        else:
            result_queue.put(_ProcessReturnResult(value=result))

    except Exception as e:
        result_queue.put(
            _ProcessErrorResult(
                error_type=type(e).__name__,
                error_message=str(e),
                traceback=tb.format_exc(),
            )
        )
    finally:
        result_queue.put(_ProcessExitResult())


async def _message_dispatcher(
    ws: WebSocket,
    queue_map: dict[int, "queue.Queue[Any]"],
) -> None:
    """
    WebSocketからすべてのメッセージを受信し、適切なmultiprocessing.Queueに直接書き込む

    Args:
        ws: WebSocketコネクション
        queue_map: キューIDとmultiprocessing.Queueのマッピング
    """
    try:
        while True:
            data = await ws.receive_bytes()
            message: Message = pickle.loads(data)

            match message:
                case QueuePutMessage(queue_id=qid, value=value):
                    await anyio.to_thread.run_sync(queue_map[qid].put, value)
                case _:  # pragma: no cover
                    raise ValueError(f"Unexpected message type: {type(message).__name__}")
    except Exception:  # pragma: no cover
        # WebSocketが閉じられたなど、エラーを無視
        pass


def _convert_rpc_queue_to_ref(
    value: Any,
    manager: Any,
    queue_map: dict[int, "queue.Queue[Any]"],
) -> Any:
    """
    _RpcQueueをQueueRefに変換し、必要なmultiprocessing.Queueを設定する

    Args:
        value: 処理する値
        manager: multiprocessing.Manager
        queue_map: キューIDとmultiprocessing.Queueのマッピング

    Returns:
        処理後の値（_RpcQueueの場合はQueueRef、それ以外はそのまま）
    """
    if isinstance(value, _RpcQueue):
        queue_id = value.queue_id
        pipe: "queue.Queue[Any]" = manager.Queue()  # type: ignore[attr-defined]
        queue_map[queue_id] = pipe
        return QueueRef(queue_id=queue_id)
    return value
