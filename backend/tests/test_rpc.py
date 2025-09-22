import pickle

from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
from fastapi.testclient import TestClient

from quicklook.rpc import Rpc, create_rpc_caller_endpoint, create_rpc_caller_endpoint_async


def square(x: int) -> int:
    """テスト用の簡単な関数: xの二乗を返す。"""
    return x * x


def fibonacci(n: int):
    """フィボナッチ数列を生成するジェネレータ。最初のn個をyield。"""
    a, b = 0, 1
    for _ in range(n):
        yield a
        a, b = b, a + b


async def async_fibonacci(n: int):
    """フィボナッチ数列を生成する非同期ジェネレータ。最初のn個をyield。"""
    a, b = 0, 1
    for _ in range(n):
        yield a
        a, b = b, a + b


async def async_square(x: int) -> int:
    """テスト用の非同期関数: xの二乗を返す。"""
    return x * x


def test_rpc_square():
    """RPCでsquare関数を実行するテスト。"""
    # RPCリクエストを作成
    rpc = Rpc.create(square, 5)

    # RPCをpickleでシリアライズ
    pickled_rpc = pickle.dumps(rpc)

    # TestClientを使ってFastAPIアプリにリクエスト
    client = TestClient(app)
    response = client.post("/rpc", content=pickled_rpc)

    # レスポンスをパース
    content = response.content
    results = []
    offset = 0
    while offset < len(content):
        if offset + 4 > len(content):
            break
        size = int.from_bytes(content[offset:offset+4], 'big')
        offset += 4
        if offset + size > len(content):
            break
        data = content[offset:offset + size]
        result = pickle.loads(data)
        results.append(result)
        offset += size

    # 結果を確認
    assert len(results) == 1
    assert results[0] == 25


def test_rpc_fibonacci_stream():
    """RPCでフィボナッチ数列をストリームとして実行するテスト。"""
    # RPCリクエストを作成
    rpc = Rpc.create(fibonacci, 5)

    # RPCをpickleでシリアライズ
    pickled_rpc = pickle.dumps(rpc)

    # TestClientを使ってFastAPIアプリにリクエスト
    client = TestClient(app)
    response = client.post("/rpc", content=pickled_rpc)

    # レスポンスをパース
    content = response.content
    results = []
    offset = 0
    while offset < len(content):
        if offset + 4 > len(content):
            break
        size = int.from_bytes(content[offset:offset+4], 'big')
        offset += 4
        if offset + size > len(content):
            break
        data = content[offset:offset + size]
        result = pickle.loads(data)
        results.append(result)
        offset += size

    # 期待されるフィボナッチ数列: [0, 1, 1, 2, 3]
    expected = [0, 1, 1, 2, 3]
    assert results == expected


def test_rpc_async_fibonacci_stream():
    """RPCで非同期フィボナッチ数列をストリームとして実行するテスト。"""
    # RPCリクエストを作成
    rpc = Rpc.create(async_fibonacci, 5)

    # RPCをpickleでシリアライズ
    pickled_rpc = pickle.dumps(rpc)

    # TestClientを使ってFastAPIアプリにリクエスト
    client = TestClient(app)
    response = client.post("/rpc-async", content=pickled_rpc)

    # レスポンスをパース
    content = response.content
    results = []
    offset = 0
    while offset < len(content):
        if offset + 4 > len(content):
            break
        size = int.from_bytes(content[offset:offset+4], 'big')
        offset += 4
        if offset + size > len(content):
            break
        data = content[offset:offset + size]
        result = pickle.loads(data)
        results.append(result)
        offset += size

    # 期待されるフィボナッチ数列: [0, 1, 1, 2, 3]
    expected = [0, 1, 1, 2, 3]
    assert results == expected


def test_rpc_async_square():
    """RPCで非同期square関数を実行するテスト。"""
    # RPCリクエストを作成
    rpc = Rpc.create(async_square, 5)

    # RPCをpickleでシリアライズ
    pickled_rpc = pickle.dumps(rpc)

    # TestClientを使ってFastAPIアプリにリクエスト
    client = TestClient(app)
    response = client.post("/rpc-async", content=pickled_rpc)

    # レスポンスをパース
    content = response.content
    results = []
    offset = 0
    while offset < len(content):
        if offset + 4 > len(content):
            break
        size = int.from_bytes(content[offset:offset+4], 'big')
        offset += 4
        if offset + size > len(content):
            break
        data = content[offset:offset + size]
        result = pickle.loads(data)
        results.append(result)
        offset += size

    # 結果を確認
    assert len(results) == 1
    assert results[0] == 25


# テスト用のFastAPIアプリケーション
app = FastAPI()


@app.post("/rpc")
async def rpc_endpoint(request: Request):
    body = await request.body()
    return StreamingResponse(create_rpc_caller_endpoint(body), media_type="application/octet-stream")


@app.post("/rpc-async")
async def rpc_async_endpoint(request: Request):
    body = await request.body()
    return StreamingResponse(create_rpc_caller_endpoint_async(body), media_type="application/octet-stream")
