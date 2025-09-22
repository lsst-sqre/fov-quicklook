import aiohttp
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
from fastapi.testclient import TestClient

import pytest

from quicklook.rpc import Rpc, create_rpc_caller_endpoint, run_rpc, run_rpc_stream
from quicklook.dev.run_uvicorn import run_uvicorn_app, find_free_tcp_port


def square(x: int) -> int:
    """テスト用の簡単な関数: xの二乗を返す。"""
    return x * x


def fibonacci(n: int):
    """フィボナッチ数列を生成するジェネレータ。最初のn個をyield。"""
    a, b = 0, 1
    for _ in range(n):
        yield a
        a, b = b, a + b


def error_generator(n: int):
    """エラーが発生するジェネレータ。最初の2つをyieldした後にValueErrorを投げる。"""
    for i in range(n):
        if i == 2:
            raise ValueError("Test error in generator")
        yield i


app = FastAPI()
client = TestClient(app)


@app.post("/rpc")
async def rpc_endpoint(request: Request):
    """RPCエンドポイント: リクエストボディをcreate_rpc_caller_endpointに渡す。"""
    body = await request.body()
    return StreamingResponse(create_rpc_caller_endpoint(body), media_type="application/octet-stream")


@app.get("/healthz")
async def healthcheck():
    """ヘルスチェックエンドポイント"""
    return {"status": "ok"}


# テスト用のFastAPIアプリ文字列（uvicorn用）
TEST_APP_MODULE = "tests.test_server_app:app"


@pytest.mark.asyncio
async def test_rpc_square_with_uvicorn():
    """uvicornサーバーを立ち上げてRPCでsquare関数を実行するテスト。"""
    port = find_free_tcp_port()
    
    with run_uvicorn_app(TEST_APP_MODULE, port=port) as wait_for_ready:
        wait_for_ready()
        
        rpc = Rpc.create(square, 5)
        result = await run_rpc(f"http://127.0.0.1:{port}/rpc", rpc)
        
        # 結果を確認
        assert result == 25


@pytest.mark.asyncio 
async def test_rpc_fibonacci_stream_with_uvicorn():
    """uvicornサーバーを立ち上げてRPCでフィボナッチ数列をストリームとして実行するテスト。"""
    port = find_free_tcp_port()
    
    with run_uvicorn_app(TEST_APP_MODULE, port=port) as wait_for_ready:
        wait_for_ready()
        
        rpc = Rpc.create(fibonacci, 5)
        results = []
        async for result in run_rpc_stream(f"http://127.0.0.1:{port}/rpc", rpc):
            results.append(result)
        
        # 結果を確認
        expected = [0, 1, 1, 2, 3]
        assert results == expected


@pytest.mark.asyncio
async def test_rpc_error_generator_stream_with_uvicorn():
    """uvicornサーバーを立ち上げてRPCでエラーが発生するジェネレータをストリームとして実行するテスト。"""
    port = find_free_tcp_port()
    
    with run_uvicorn_app(TEST_APP_MODULE, port=port) as wait_for_ready:
        wait_for_ready()
        
        rpc = Rpc.create(error_generator, 5)
        results = []
        try:
            async for result in run_rpc_stream(f"http://127.0.0.1:{port}/rpc", rpc):
                results.append(result)
            assert False, "Should have raised ValueError"
        except ValueError as e:
            # 最初の2つは正常にyieldされ、3つ目はValueError
            assert str(e) == "Test error in generator"
            assert len(results) == 2
            assert results[0] == 0
            assert results[1] == 1


@pytest.mark.asyncio
async def test_rpc_timeout_error():
    """タイムアウトエラーのテスト。"""
    import aiohttp
    
    rpc = Rpc.create(square, 5)
    
    # 存在しないホストに対してタイムアウトテスト
    with pytest.raises(Exception):  # ConnectionError またはTimeoutError
        await run_rpc(
            "http://localhost:99999/rpc", 
            rpc, 
            timeout=aiohttp.ClientTimeout(total=0.1)
        )


@pytest.mark.asyncio
async def test_rpc_server_error_handling():
    """サーバーエラーのハンドリングテスト。"""
    port = find_free_tcp_port()
    
    # 間違ったエンドポイントにリクエストして404エラーを発生させる
    with run_uvicorn_app(TEST_APP_MODULE, port=port) as wait_for_ready:
        wait_for_ready()
        
        rpc = Rpc.create(square, 5)
        
        # 存在しないエンドポイントへのリクエスト
        with pytest.raises(aiohttp.ClientResponseError):
            await run_rpc(f"http://127.0.0.1:{port}/nonexistent", rpc)
