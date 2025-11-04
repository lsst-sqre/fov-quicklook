"""
テスト用のFastAPIアプリケーション。

uvicornサーバーでRPCテストを行うための専用アプリ。
tests/test_rpc.pyからimportされる。
"""

from fastapi import FastAPI, WebSocket

from quicklook.rpc.lifespan import rpc_lifespan
from quicklook.rpc.server import create_rpc_endpoint as create_ws_rpc_endpoint

app = FastAPI(lifespan=rpc_lifespan)


@app.websocket("/rpc")
async def websocket_rpc_endpoint(websocket: WebSocket):
    """RPCエンドポイント (WebSocket): 新しいRPC実装"""
    await create_ws_rpc_endpoint(app, websocket)


@app.get("/healthz")
async def healthcheck():
    """ヘルスチェックエンドポイント"""
    return {"status": "ok"}