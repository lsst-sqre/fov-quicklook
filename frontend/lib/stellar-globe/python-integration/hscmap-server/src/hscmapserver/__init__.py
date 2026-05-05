import secrets
from dataclasses import dataclass, field
from logging import getLogger
from pathlib import Path
from typing import Any

from fastapi import FastAPI, WebSocket
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

app = FastAPI()
logger = getLogger(__name__)


@app.get("/")
def home():
    return FileResponse("static/dist/index.html")


Path('./static/dist/assets').mkdir(parents=True, exist_ok=True)
app.mount("/assets", StaticFiles(directory="static/dist/assets"), name="assets")


@dataclass
class Relay:
    comm_id: str
    server: WebSocket
    client: WebSocket | None = None
    client_buffer: list = field(default_factory=list)

    async def close(self):
        if self.server:
            await self.server.close()
        if self.client:
            await self.client.close()

    async def connect_from_client(self, ws: WebSocket):
        assert self.client is None
        self.client = ws
        while len(self.client_buffer) > 0:
            await self.client.send_json(self.client_buffer.pop(0))

    async def send_to_client(self, data: Any):
        if self.client:
            await self.client.send_json(data)
        else:
            self.client_buffer.append(data)


relays: dict[str, Relay] = {}


@app.websocket("/comms")
async def server_endpoint(ws: WebSocket):
    await ws.accept()
    open_msg = await ws.receive_json()
    comm_id = secrets.token_urlsafe(32)
    await ws.send_json({"comm_id": comm_id})
    relay = Relay(comm_id, server=ws)
    relays[comm_id] = relay
    await relay.send_to_client(open_msg)
    try:
        while True:
            data = await ws.receive_json()
            await relay.send_to_client(data)
    except:
        await relay.close()
        del relays[comm_id]


@app.websocket("/comms/{comm_id}")
async def client_endpoint(comm_id: str, ws: WebSocket):
    await ws.accept()
    relay = relays.get(comm_id)
    if not relay:
        await ws.close()
        return
    await relay.connect_from_client(ws)
    try:
        while True:
            data = await ws.receive_json()
            await relay.server.send_json(data)
    except:
        await relay.close()
        del relays[comm_id]
