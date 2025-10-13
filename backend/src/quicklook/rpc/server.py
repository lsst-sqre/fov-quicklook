import asyncio
import inspect
import multiprocessing as mp
import pickle
import traceback as tb
from collections.abc import Callable
from typing import Any

import anyio.to_thread
from fastapi import FastAPI, WebSocket

from .lifespan import get_manager, get_process_pool
from .types import (
    CallMessage,
    ErrorMessage,
    Message,
    QueueDoneMessage,
    QueuePutMessage,
    ReturnMessage,
    YieldMessage,
)


class _QueueProxy:
    """multiprocessing.Queueをqueue.Queueインターフェースでラップする"""
    
    def __init__(self, mq: Any):  # mp.Queue type
        self._mq = mq
    
    def get(self, block: bool = True, timeout: float | None = None) -> Any:
        return self._mq.get(block=block, timeout=timeout)
    
    def put(self, item: Any, block: bool = True, timeout: float | None = None) -> None:
        self._mq.put(item, block=block, timeout=timeout)


def _execute_function_in_process(
    func: Callable[..., Any],
    args: tuple[Any, ...],
    kwargs: dict[str, Any],
    queue_map: dict[int, Any],  # dict[int, mp.Queue]
    result_queue: Any,  # mp.Queue
) -> None:
    """
    プロセス内で関数を実行し、結果をresult_queueに送信する
    
    Args:
        func: 実行する関数
        args: 位置引数 (キューIDは整数として含まれる)
        kwargs: キーワード引数 (キューIDは整数として含まれる)
        queue_map: キューIDとmultiprocessing.Queueのマッピング
        result_queue: 結果を送信するmultiprocessing.Queue
    """
    # 非同期関数はサポートしない
    if inspect.iscoroutinefunction(func):  # pragma: no branch
        result_queue.put(
            (
                "error",
                {
                    "error_type": "TypeError",
                    "error_message": "Async functions are not supported in RPC",
                    "traceback": "",
                },
            )
        )
        return

    try:
        # argsとkwargsの中のキューIDインデックスをqueue.Queueに置き換え
        processed_args = []
        for arg in args:
            if isinstance(arg, int) and arg in queue_map:
                processed_args.append(_QueueProxy(queue_map[arg]))
            else:
                processed_args.append(arg)
        
        processed_kwargs = {}
        for k, v in kwargs.items():
            if isinstance(v, int) and v in queue_map:
                processed_kwargs[k] = _QueueProxy(queue_map[v])
            else:
                processed_kwargs[k] = v

        result = func(*processed_args, **processed_kwargs)

        # ジェネレータの場合
        if inspect.isgenerator(result):
            for item in result:
                result_queue.put(("yield", item))
            result_queue.put(("return", None))
        else:
            result_queue.put(("return", result))

    except Exception as e:
        result_queue.put(
            (
                "error",
                {
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                    "traceback": tb.format_exc(),
                },
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
        
        # RpcQueueのマッピングを作成
        queue_map: dict[int, Any] = {}  # dict[int, mp.Queue]
        queue_tasks: list[asyncio.Task[None]] = []

        # argsとkwargsからRpcQueueを抽出してキューIDに置き換え
        processed_args = []
        for arg in args:
            if hasattr(arg, "__class__") and arg.__class__.__name__ == "_RpcQueue":
                queue_id = arg.queue_id
                pipe: Any = manager.Queue()  # type: ignore[attr-defined]
                queue_map[queue_id] = pipe
                processed_args.append(queue_id)
                # キューメッセージを受信するタスクを作成
                queue_tasks.append(
                    asyncio.create_task(_handle_queue_messages(ws, queue_id, pipe))
                )
            else:
                processed_args.append(arg)

        processed_kwargs = {}
        for k, v in kwargs.items():
            if hasattr(v, "__class__") and v.__class__.__name__ == "_RpcQueue":
                queue_id = v.queue_id
                pipe: Any = manager.Queue()  # type: ignore[attr-defined]
                queue_map[queue_id] = pipe
                processed_kwargs[k] = queue_id
                queue_tasks.append(
                    asyncio.create_task(_handle_queue_messages(ws, queue_id, pipe))
                )
            else:
                processed_kwargs[k] = v

        # 結果を受信するキュー
        result_queue: Any = manager.Queue()  # type: ignore[attr-defined]

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
            msg_type, value = await anyio.to_thread.run_sync(result_queue.get)

            match msg_type:
                case "yield":
                    yield_msg = YieldMessage(value=value)
                    await ws.send_bytes(pickle.dumps(yield_msg))
                case "return":
                    return_msg = ReturnMessage(value=value)
                    await ws.send_bytes(pickle.dumps(return_msg))
                    break
                case "error":
                    error_response = ErrorMessage(
                        error_type=value["error_type"],
                        error_message=value["error_message"],
                        traceback=value["traceback"],
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
        await ws.close()


async def _handle_queue_messages(
    ws: WebSocket, queue_id: int, pipe: Any  # mp.Queue
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
