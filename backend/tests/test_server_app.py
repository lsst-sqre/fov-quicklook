"""
テスト用のFastAPIアプリケーション。

uvicornサーバーでRPCテストを行うための専用アプリ。
tests/test_rpc.pyからimportされる。
"""

from fastapi import FastAPI, Request, WebSocket
from fastapi.responses import StreamingResponse

from quicklook.comm.rpc import create_rpc_caller_endpoint
from quicklook.rpc.lifespan import rpc_lifespan
from quicklook.rpc.server import create_rpc_endpoint as create_ws_rpc_endpoint

app = FastAPI(lifespan=rpc_lifespan)


@app.post("/rpc")
async def rpc_endpoint(request: Request):
    """RPCエンドポイント (HTTP): リクエストボディをcreate_rpc_caller_endpointに渡す。"""
    body = await request.body()
    return StreamingResponse(create_rpc_caller_endpoint(body), media_type="application/octet-stream")


@app.websocket("/rpc")
async def websocket_rpc_endpoint(websocket: WebSocket):
    """RPCエンドポイント (WebSocket): 新しいRPC実装"""
    await create_ws_rpc_endpoint(app, websocket)


@app.get("/healthz")
async def healthcheck():
    """ヘルスチェックエンドポイント"""
    return {"status": "ok"}