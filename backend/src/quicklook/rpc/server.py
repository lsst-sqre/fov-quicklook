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
    Message,
    QueueDoneMessage,
    QueuePutMessage,
    QueueRef,
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
class _ProcessErrorResult:
    """プロセスからのエラー結果"""

    error_type: str
    error_message: str
    traceback: str


_ProcessResult = _ProcessYieldResult | _ProcessReturnResult | _ProcessErrorResult


class _QueueProxy(Generic[T]):
    """multiprocessing.Queueをqueue.Queueインターフェースでラップする"""

    def __init__(self, mq: Any):  # mp.Queue type
        self._mq = mq

    def get(self, block: bool = True, timeout: float | None = None) -> T:
        return self._mq.get(block=block, timeout=timeout)  # type: ignore[no-any-return]

    def put(self, item: T, block: bool = True, timeout: float | None = None) -> None:
        self._mq.put(item, block=block, timeout=timeout)


def _process_args_kwargs_with_queue_map(
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
    processed_args = []
    for arg in args:
        if isinstance(arg, QueueRef):
            processed_args.append(_QueueProxy(queue_map[arg.queue_id]))
        else:
            processed_args.append(arg)
    
    processed_kwargs = {}
    for k, v in kwargs.items():
        if isinstance(v, QueueRef):
            processed_kwargs[k] = _QueueProxy(queue_map[v.queue_id])
        else:
            processed_kwargs[k] = v
    
    return processed_args, processed_kwargs


def _extract_rpc_queues(
    args: tuple[Any, ...],
    kwargs: dict[str, Any],
    manager: Any,
    ws: WebSocket,
) -> tuple[
    list[Any],
    dict[str, Any],
    dict[int, "queue.Queue[Any]"],
    list[asyncio.Task[None]],
]:
    """
    argsとkwargsからRpcQueueを抽出してQueueRefに置き換え
    
    Args:
        args: 位置引数
        kwargs: キーワード引数
        manager: multiprocessingのManager
        ws: WebSocketコネクション
    
    Returns:
        処理済みのargs, kwargs, queue_map, queue_tasks
    """
    queue_map: dict[int, "queue.Queue[Any]"] = {}
    queue_tasks: list[asyncio.Task[None]] = []

    processed_args = []
    for arg in args:
        if isinstance(arg, _RpcQueue):
            queue_id = arg.queue_id
            pipe: "queue.Queue[Any]" = manager.Queue()  # type: ignore[attr-defined]
            queue_map[queue_id] = pipe
            processed_args.append(QueueRef(queue_id=queue_id))
            queue_tasks.append(
                asyncio.create_task(_handle_queue_messages(ws, queue_id, pipe))
            )
        else:
            processed_args.append(arg)

    processed_kwargs = {}
    for k, v in kwargs.items():
        if isinstance(v, _RpcQueue):
            queue_id = v.queue_id
            pipe: "queue.Queue[Any]" = manager.Queue()  # type: ignore[attr-defined]
            queue_map[queue_id] = pipe
            processed_kwargs[k] = QueueRef(queue_id=queue_id)
            queue_tasks.append(
                asyncio.create_task(_handle_queue_messages(ws, queue_id, pipe))
            )
        else:
            processed_kwargs[k] = v

    return processed_args, processed_kwargs, queue_map, queue_tasks


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

    try:
        # argsとkwargsの中のキューIDインデックスをqueue.Queueに置き換え
        processed_args, processed_kwargs = _process_args_kwargs_with_queue_map(
            args, kwargs, queue_map
        )

        result = func(*processed_args, **processed_kwargs)

        # ジェネレータの場合
        if inspect.isgenerator(result):
            for item in result:
                result_queue.put(_ProcessYieldResult(value=item))
            result_queue.put(_ProcessReturnResult(value=None))
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
        
        # argsとkwargsからRpcQueueを抽出してキューIDに置き換え
        processed_args, processed_kwargs, queue_map, queue_tasks = _extract_rpc_queues(
            args, kwargs, manager, ws
        )

        # 結果を受信するキュー
        result_queue: "queue.Queue[_ProcessResult]" = manager.Queue()  # type: ignore[attr-defined]

        # プロセスプールで関数を実行
        pool = get_process_pool(app)

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
                    break
                case _ProcessErrorResult(error_type=error_type, error_message=error_message, traceback=traceback):
                    error_response = ErrorMessage(
                        error_type=error_type,
                        error_message=error_message,
                        traceback=traceback,
                    )
                    await ws.send_bytes(pickle.dumps(error_response))
                    break

        # キューのタスクをキャンセル
        for task in queue_tasks:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

    except Exception as e:
        # エラーをクライアントに送信
        error_msg = ErrorMessage(
            error_type=type(e).__name__,
            error_message=str(e),
            traceback=tb.format_exc(),
        )
        try:
            await ws.send_bytes(pickle.dumps(error_msg))
        except Exception:  # pragma: no cover
            pass

    finally:
        try:
            await ws.close()
        except RuntimeError:  # pragma: no cover
            # WebSocketが既に閉じられている場合
            pass


async def _handle_queue_messages(
    ws: WebSocket, queue_id: int, pipe: "queue.Queue[Any]"
) -> None:
    """
    クライアントからのキューメッセージを処理してmultiprocessing.Queueにputする
    
    Args:
        ws: WebSocketコネクション
        queue_id: キューのID
        pipe: 対象のmultiprocessing.Queue
    """
    while True:
        try:
            data = await ws.receive_bytes()
            message: Message = pickle.loads(data)

            match message:
                case QueuePutMessage(queue_id=msg_queue_id, value=value):
                    if msg_queue_id == queue_id:
                        pipe.put(value)
                case QueueDoneMessage(queue_id=msg_queue_id):
                    if msg_queue_id == queue_id:
                        pipe.put(None)
                        return

        except asyncio.CancelledError:
            raise
        except Exception:  # pragma: no cover
            return
