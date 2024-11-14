import asyncio
import pickle
from typing import Annotated

import starlette
import starlette.websockets
from fastapi import APIRouter, BackgroundTasks, WebSocket
from pydantic import BaseModel
from sqlalchemy.orm import Session

from quicklook.coordinator.api.job import run_next_job
from quicklook.types import Visit
from quicklook.utils.websocket import safe_websocket

from ..quicklook import Quicklook

router = APIRouter()


class QuicklookCreate(BaseModel):
    visit: Visit


@router.post("/quicklooks")
async def create_quicklook(
    parmas: QuicklookCreate,
    background_tasks: BackgroundTasks,
):
    visit = parmas.visit
    Quicklook.enqueue(visit)
    background_tasks.add_task(run_next_job)


@router.websocket("/quicklooks/*/events.ws")
async def quicklook_events(
    ws: WebSocket,
):
    await ws.accept()
    async with safe_websocket(ws):

        async def send_events():
            async for events in Quicklook.subscribe():
                await ws.send_bytes(pickle.dumps(events))

        try:
            async with asyncio.TaskGroup() as tg:
                tg.create_task(ws.receive_text())  # check connection
                tg.create_task(send_events())
        except* starlette.websockets.WebSocketDisconnect:
            pass


@router.delete("/quicklooks/*")
async def delete_all_quicklooks():
    await Quicklook.delete_all()
