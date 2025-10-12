import asyncio
import inspect
import multiprocessing as mp
import pickle
import queue
import traceback as tb
from collections.abc import Callable, Iterator
from typing import TYPE_CHECKING, Any

from fastapi import FastAPI, WebSocket

from .lifespan import get_process_pool
from .types import (
    CallMessage,
    ErrorMessage,
    Message,
    QueueDoneMessage,
    QueuePutMessage,
    ReturnMessage,
    YieldMessage,
)

if TYPE_CHECKING:
    from multiprocessing.queues import Queue as MPQueue
else:
    MPQueue = mp.Queue


class _QueueProxy:
    """multiprocessing.Queueをqueue.Queueインターフェースでラップする"""
    
    def __init__(self, mq: "MPQueue[Any]"):
        self._mq = mq
    
    def get(self, block: bool = True, timeout: float | None = None) -> Any:
        return self._mq.get(block=block, timeout=timeout)
    
    def put(self, item: Any, block: bool = True, timeout: float | None = None) -> None:
        self._mq.put(item, block=block, timeout=timeout)


def _execute_function_in_process(
    func: Callable[..., Any],
    args: tuple[Any, ...],
    kwargs: dict[str, Any],
    queue_map: dict[int, "MPQueue[Any]"],
    result_queue: "MPQueue[tuple[str, Any]]",
) -> None:
    """
    プロセス内で関数を実行し、結果をresult_queueに送信する
    
    Args:
        func: 実行する関数
        args: 位置引数 (キューIDは_QueueProxyインスタンスとして含まれる)
        kwargs: キーワード引数 (キューIDは_QueueProxyインスタンスとして含まれる)
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

        if message["type"] != "call":  # pragma: no branch
            raise ValueError(f"Expected 'call' message, got {message['type']}")

        call_msg: CallMessage = message  # type: ignore
        func = call_msg["func"]
        args = call_msg["args"]
        kwargs = call_msg["kwargs"]

        # RpcQueueのマッピングを作成
        queue_map: dict[int, "MPQueue[Any]"] = {}
        queue_tasks: list[asyncio.Task[None]] = []

        # argsとkwargsからRpcQueueを抽出してキューIDに置き換え
        processed_args = []
        for arg in args:
            if hasattr(arg, "__class__") and arg.__class__.__name__ == "RpcQueue":
                queue_id = arg.queue_id
                pipe: "MPQueue[Any]" = mp.Queue()
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
            if hasattr(v, "__class__") and v.__class__.__name__ == "RpcQueue":
                queue_id = v.queue_id
                pipe: "MPQueue[Any]" = mp.Queue()
                queue_map[queue_id] = pipe
                processed_kwargs[k] = queue_id
                queue_tasks.append(
                    asyncio.create_task(_handle_queue_messages(ws, queue_id, pipe))
                )
            else:
                processed_kwargs[k] = v

        # 結果を受信するキュー
        result_queue: "MPQueue[tuple[str, Any]]" = mp.Queue()

        # プロセスプールで関数を実行
        pool = get_process_pool(app)
        loop = asyncio.get_event_loop()

        # 関数をプロセスで実行（非同期で実行、結果はresult_queueに送信される）
        loop.run_in_executor(
            pool,
            _execute_function_in_process,
            func,
            tuple(processed_args),
            processed_kwargs,
            queue_map,
            result_queue,
        )

        # result_queueから結果を受信してクライアントに送信
        while True:
            # 非ブロッキングで結果を取得
            try:
                msg_type, value = await loop.run_in_executor(
                    None, result_queue.get, True, 0.1
                )
            except queue.Empty:
                # WebSocketが閉じられたかチェック
                await asyncio.sleep(0)
                continue

            match msg_type:
                case "yield":
                    yield_msg: YieldMessage = {"type": "yield", "value": value}
                    await ws.send_bytes(pickle.dumps(yield_msg))
                case "return":
                    return_msg: ReturnMessage = {"type": "return", "value": value}
                    await ws.send_bytes(pickle.dumps(return_msg))
                    break
                case "error":
                    error_response: ErrorMessage = {
                        "type": "error",
                        "error_type": value["error_type"],
                        "error_message": value["error_message"],
                        "traceback": value["traceback"],
                    }
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
        error_msg: ErrorMessage = {
            "type": "error",
            "error_type": type(e).__name__,
            "error_message": str(e),
            "traceback": tb.format_exc(),
        }
        try:
            await ws.send_bytes(pickle.dumps(error_msg))
        except:  # pragma: no cover
            pass

    finally:
        await ws.close()


async def _handle_queue_messages(
    ws: WebSocket, queue_id: int, pipe: "MPQueue[Any]"
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

            match message["type"]:
                case "queue_put":
                    queue_msg: QueuePutMessage = message  # type: ignore
                    if queue_msg["queue_id"] == queue_id:
                        pipe.put(queue_msg["value"])
                case "queue_done":
                    done_msg: QueueDoneMessage = message  # type: ignore
                    if done_msg["queue_id"] == queue_id:
                        pipe.put(None)
                        return

        except asyncio.CancelledError:
            raise
        except Exception:  # pragma: no cover
            return
