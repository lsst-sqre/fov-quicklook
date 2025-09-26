"""
テスト用のFastAPIアプリケーション。

uvicornサーバーでRPCテストを行うための専用アプリ。
tests/test_rpc.pyからimportされる。
"""

from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse

from quicklook.comm.rpc import create_rpc_caller_endpoint

app = FastAPI()


@app.post("/rpc")
async def rpc_endpoint(request: Request):
    """RPCエンドポイント: リクエストボディをcreate_rpc_caller_endpointに渡す。"""
    body = await request.body()
    return StreamingResponse(create_rpc_caller_endpoint(body), media_type="application/octet-stream")


@app.get("/healthz")
async def healthcheck():
    """ヘルスチェックエンドポイント"""
    return {"status": "ok"}