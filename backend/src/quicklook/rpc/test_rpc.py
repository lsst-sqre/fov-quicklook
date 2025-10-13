import asyncio
import pickle
import queue
from typing import Generator

import pytest
import uvicorn
from fastapi import FastAPI, WebSocket

from quicklook.rpc import Rpc, _RpcQueue, RpcRemoteError, create_rpc_endpoint, rpc_lifespan
from quicklook.rpc.lifespan import AppState
from quicklook.rpc.queue import RpcQueue
from quicklook.rpc.types import ErrorMessage, YieldMessage


def simple_function(x: int, y: int) -> int:
    """シンプルな関数"""
    return x + y


def generator_function(n: int):
    """ジェネレータ関数"""
    for i in range(n):
        yield i


def error_function():
    """エラーを発生させる関数"""
    raise ValueError("Test error")


async def async_function():
    """非同期関数（サポートされない）"""
    await asyncio.sleep(0.1)
    return "async result"


def queue_consumer_function(q: queue.Queue) -> list[int]:
    """キューから値を受け取る関数"""
    results = []
    while True:
        item = q.get()
        if item is None:
            break
        results.append(item * 2)
    return results


def queue_generator_function(q: queue.Queue[int]) -> Generator[int]:
    """キューから値を受け取ってyieldする関数"""
    while True:
        item = q.get()
        if item is None:
            break
        yield item * 2


def function_with_int_arg(value: int) -> int:
    """整数を受け取って2倍にする関数"""
    return value * 2


@pytest.fixture
async def rpc_app():
    """テスト用のFastAPIアプリケーション"""
    app = FastAPI(lifespan=rpc_lifespan)

    @app.websocket("/rpc")
    async def rpc_endpoint(ws: WebSocket):
        await create_rpc_endpoint(app, ws)

    return app


@pytest.fixture
async def rpc_server(rpc_app):
    """テスト用のサーバーを起動"""
    config = uvicorn.Config(rpc_app, host="127.0.0.1", port=8765, log_level="error")
    server = uvicorn.Server(config)

    # サーバーをバックグラウンドで起動
    task = asyncio.create_task(server.serve())

    # サーバーが起動するまで待機
    await asyncio.sleep(0.5)

    yield "ws://127.0.0.1:8765/rpc"

    # サーバーをシャットダウン
    server.should_exit = True
    await task


async def test_simple_function(rpc_server):
    """シンプルな関数のRPC呼び出しをテスト"""
    result = await Rpc(rpc_server, simple_function, 3, 5).run()
    assert result == 8


async def test_generator_function(rpc_server):
    """ジェネレータ関数のRPC呼び出しをテスト"""
    results = []
    result = await Rpc(rpc_server, generator_function, 5).run()
    async for item in result:  # type: ignore[union-attr]
        results.append(item)
    assert results == [0, 1, 2, 3, 4]


async def test_error_function(rpc_server):
    """エラーが発生する関数のRPC呼び出しをテスト"""
    with pytest.raises(RpcRemoteError) as exc_info:
        await Rpc(rpc_server, error_function).run()

    assert exc_info.value.error_type == "ValueError"
    assert "Test error" in exc_info.value.error_message


async def test_async_function_not_supported(rpc_server):
    """非同期関数がサポートされないことをテスト"""
    with pytest.raises(RpcRemoteError) as exc_info:
        await Rpc(rpc_server, async_function).run()

    assert exc_info.value.error_type == "TypeError"
    assert "Async functions are not supported" in exc_info.value.error_message


async def test_queue_consumer(rpc_server):
    """キューを使った関数のRPC呼び出しをテスト"""
    client_queue = asyncio.Queue()

    async def produce():
        for i in range(3):
            await client_queue.put(i)
        await client_queue.put(None)

    task = asyncio.create_task(produce())
    result = await Rpc(rpc_server, queue_consumer_function, RpcQueue(client_queue)).run()

    await task
    assert result == [0, 2, 4]


async def test_queue_generator(rpc_server):
    """キューを使ったジェネレータのRPC呼び出しをテスト"""
    client_queue = asyncio.Queue()

    async def produce():
        for i in range(3):
            await client_queue.put(i)
            await asyncio.sleep(0.01)
        await client_queue.put(None)

    task = asyncio.create_task(produce())

    results = []
    result = await Rpc(rpc_server, queue_generator_function, RpcQueue(client_queue)).run()
    async for item in result:  # type: ignore[union-attr]
        results.append(item)

    await task
    assert results == [0, 2, 4]


async def test_kwargs(rpc_server):
    """キーワード引数を使ったRPC呼び出しをテスト"""
    result = await Rpc(rpc_server, simple_function, x=10, y=20).run()
    assert result == 30


async def test_mixed_args_kwargs(rpc_server):
    """位置引数とキーワード引数を混ぜたRPC呼び出しをテスト"""
    result = await Rpc(rpc_server, simple_function, 15, y=25).run()
    assert result == 40


async def test_integer_argument_not_confused_with_queue(rpc_server):
    """整数引数がキュー参照と混同されないことをテスト"""
    # queue_idと同じ値の整数を渡しても正しく処理される
    result = await Rpc(rpc_server, function_with_int_arg, 0).run()
    assert result == 0

    result = await Rpc(rpc_server, function_with_int_arg, 1).run()
    assert result == 2

    result = await Rpc(rpc_server, function_with_int_arg, 100).run()
    assert result == 200


async def test_invalid_message_type(rpc_app):
    """無効なメッセージタイプをテスト"""
    import websockets

    # サーバーを起動
    config = uvicorn.Config(rpc_app, host="127.0.0.1", port=8766, log_level="error")
    server = uvicorn.Server(config)
    task = asyncio.create_task(server.serve())
    await asyncio.sleep(0.5)

    try:
        async with websockets.connect("ws://127.0.0.1:8766/rpc") as ws:
            # 無効なメッセージを送信
            invalid_msg = YieldMessage(value=123)
            await ws.send(pickle.dumps(invalid_msg))

            # エラーメッセージを受信
            data = await ws.recv()
            if isinstance(data, bytes):
                message = pickle.loads(data)
                assert isinstance(message, ErrorMessage)
                assert "Expected CallMessage" in message.error_message
    finally:
        server.should_exit = True
        await task


async def test_connection_error_handling(rpc_app):
    """接続エラー時の処理をテスト"""
    # 存在しないサーバーに接続を試みる
    with pytest.raises(Exception):  # websockets.exceptions.* or OSError
        await Rpc("ws://127.0.0.1:19999/rpc", simple_function, 1, 2).run()


async def test_lifespan_error_handling():
    """lifespanのエラーハンドリングをテスト"""
    from quicklook.rpc.lifespan import get_process_pool, get_manager

    # 初期化されていない状態でアクセス
    app = FastAPI()
    app.state.rpc = AppState()

    with pytest.raises(RuntimeError, match="Process pool is not initialized"):
        get_process_pool(app)

    with pytest.raises(RuntimeError, match="Manager is not initialized"):
        get_manager(app)
