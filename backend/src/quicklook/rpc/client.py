import asyncio
import pickle
from collections.abc import AsyncIterator, Callable, Generator
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, Any, Generic, ParamSpec, TypeVar

import websockets

from .queue import _RpcQueue

if TYPE_CHECKING:
    from websockets.asyncio.client import ClientConnection

from .types import (
    CallMessage,
    ErrorMessage,
    ExitMessage,
    Message,
    QueuePutMessage,
    ResponseTypeMessage,
    ReturnMessage,
    RpcRemoteError,
    YieldMessage,
)

P = ParamSpec("P")
T = TypeVar("T")
R = TypeVar("R")


class Rpc(Generic[P, R]):
    """
    リモート関数呼び出しを行うクライアントクラス

    使用例:
        # 通常の関数
        result = await Rpc(endpoint_url, func, arg1, arg2).run()

        # ジェネレータ関数
        async for item in Rpc(endpoint_url, func, arg1, arg2).iterate():
            print(item)
    """

    def __init__(
        self,
        endpoint_url: str,
        func: Callable[P, R] | Callable[P, Generator[R, Any, Any]],
        *args: P.args,
        **kwargs: P.kwargs,
    ):
        self.endpoint_url = endpoint_url
        self.func = func
        self.args = args
        self.kwargs = kwargs

    async def run(self) -> R:
        ws = await websockets.connect(self.endpoint_url)

        try:
            async with _handle_rpc_arguments(self.args, self.kwargs, ws):
                call_msg = CallMessage(
                    func=self.func,
                    args=self.args,
                    kwargs=self.kwargs,
                )
                await ws.send(pickle.dumps(call_msg))

                # 最初のメッセージを受信（ResponseType or Error）
                data = await ws.recv()
                if isinstance(data, str):  # pragma: no cover
                    raise RuntimeError("Unexpected string message")
                message: Message = pickle.loads(data)  # type: ignore[arg-type]
                
                # 最初のメッセージがErrorの場合（ResponseType送信前のエラー）
                if isinstance(message, ErrorMessage):
                    error = RpcRemoteError(message.error_type, message.error_message, message.traceback)
                    # Exitを待つ
                    async for data in ws:
                        if isinstance(data, str):  # pragma: no cover
                            continue
                        msg: Message = pickle.loads(data)  # type: ignore[arg-type]
                        if isinstance(msg, ExitMessage):
                            break
                    raise error
                
                # ResponseTypeMessage以外は期待しない
                if not isinstance(message, ResponseTypeMessage):  # pragma: no branch
                    raise RuntimeError(f"Expected ResponseTypeMessage, got {type(message).__name__}")

                if message.is_generator:  # pragma: no branch
                    raise RuntimeError(f"Expected non-generator function, but {self.func.__name__} is a generator")

                # 結果を受信
                return_value: R | None = None
                error: RpcRemoteError | None = None

                async for data in ws:
                    if isinstance(data, str):  # pragma: no cover
                        continue
                    msg: Message = pickle.loads(data)  # type: ignore[arg-type]
                    match msg:
                        case ReturnMessage(value=value):
                            return_value = value  # type: ignore[assignment]
                        case ErrorMessage(error_type=error_type, error_message=error_message, traceback=traceback):
                            error = RpcRemoteError(error_type, error_message, traceback)
                        case ExitMessage():
                            break
                        case _:  # pragma: no cover
                            raise RuntimeError(f"Unexpected message type: {type(msg).__name__}")

                # Exitを受信した後にエラーまたは戻り値を返す
                if error is not None:
                    raise error
                if return_value is not None:
                    return return_value  # type: ignore[return-value]
                raise RuntimeError(f"No return value received from {self.func.__name__}")
        finally:
            await self._close(ws)

    async def iterate(self) -> AsyncIterator[R]:
        ws = await websockets.connect(self.endpoint_url)

        try:
            async with _handle_rpc_arguments(self.args, self.kwargs, ws):
                call_msg = CallMessage(
                    func=self.func,
                    args=self.args,
                    kwargs=self.kwargs,
                )
                await ws.send(pickle.dumps(call_msg))

                # 最初のメッセージを受信（ResponseType or Error）
                data = await ws.recv()
                if isinstance(data, str):  # pragma: no cover
                    raise RuntimeError("Unexpected string message")
                message: Message = pickle.loads(data)  # type: ignore[arg-type]
                
                # 最初のメッセージがErrorの場合（ResponseType送信前のエラー）
                if isinstance(message, ErrorMessage):
                    error = RpcRemoteError(message.error_type, message.error_message, message.traceback)
                    # Exitを待つ
                    async for data in ws:
                        if isinstance(data, str):  # pragma: no cover
                            continue
                        msg: Message = pickle.loads(data)  # type: ignore[arg-type]
                        if isinstance(msg, ExitMessage):
                            break
                    raise error
                
                # ResponseTypeMessage以外は期待しない
                if not isinstance(message, ResponseTypeMessage):  # pragma: no branch
                    raise RuntimeError(f"Expected ResponseTypeMessage, got {type(message).__name__}")

                if not message.is_generator:  # pragma: no branch
                    raise RuntimeError(f"Expected generator function, but {self.func.__name__} is not a generator")

                # 結果を受信
                error: RpcRemoteError | None = None

                async for data in ws:
                    if isinstance(data, str):  # pragma: no cover
                        continue

                    msg: Message = pickle.loads(data)  # type: ignore[arg-type]

                    match msg:
                        case YieldMessage(value=value):
                            yield value
                        case ReturnMessage(value=value):
                            yield value
                        case ErrorMessage(error_type=error_type, error_message=error_message, traceback=traceback):
                            error = RpcRemoteError(error_type, error_message, traceback)
                        case ExitMessage():
                            break
                        case _:  # pragma: no cover
                            raise RuntimeError(f"Unexpected message type: {type(msg).__name__}")

                # Exitを受信した後にエラーがあれば発生させる
                if error is not None:
                    raise error
        finally:
            await self._close(ws)

    async def _close(self, ws: "ClientConnection") -> None:
        try:
            await ws.close()
        except Exception:  # pragma: no cover
            pass


@asynccontextmanager
async def _handle_rpc_arguments(
    args: tuple[Any, ...],
    kwargs: dict[str, Any],
    ws: "ClientConnection",
) -> AsyncIterator[None]:
    tasks: list[asyncio.Task] = []
    try:
        # キュー送信タスクを起動
        for arg in args:
            if isinstance(arg, _RpcQueue):
                task = asyncio.create_task(_send_queue_messages_helper(ws, arg.queue_id, arg.queue))
                tasks.append(task)

        for v in kwargs.values():
            if isinstance(v, _RpcQueue):
                task = asyncio.create_task(_send_queue_messages_helper(ws, v.queue_id, v.queue))
                tasks.append(task)

        yield
    finally:
        # タスクをキャンセル
        for task in tasks:
            task.cancel()
        
        # キャンセル完了を待つ
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)


async def _send_queue_messages_helper(ws: "ClientConnection", queue_id: int, q: asyncio.Queue[Any]) -> None:
    while True:
        item = await q.get()
        put_msg = QueuePutMessage(queue_id=queue_id, value=item)
        await ws.send(pickle.dumps(put_msg))
