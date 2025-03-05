import asyncio
import pickle

import starlette
import starlette.websockets
from fastapi import APIRouter, BackgroundTasks, WebSocket
from pydantic import BaseModel

from quicklook.coordinator.run_quicklookjob import run_next_job
from quicklook.types import Visit
from quicklook.utils.websocket import safe_websocket

from ..quicklookjob import QuicklookJob

router = APIRouter()


class QuicklookCreate(BaseModel):
    visit: Visit


@router.post("/quicklooks")
async def create_quicklook(
    parmas: QuicklookCreate,
    background_tasks: BackgroundTasks,
):
    visit = parmas.visit
    QuicklookJob.enqueue(visit)
    background_tasks.add_task(run_next_job)


@router.delete("/quicklooks/*")
async def delete_all_quicklooks():
    await QuicklookJob.delete_all()


@router.websocket("/quicklook-jobs/events.ws")
async def quicklook_events(
    ws: WebSocket,
):
    await ws.accept()
    async with safe_websocket(ws):

        async def send_events():
            async for events in QuicklookJob.subscribe():
                await ws.send_bytes(pickle.dumps(events))

        try:
            async with asyncio.TaskGroup() as tg:
                tg.create_task(ws.receive_text())  # check connection
                tg.create_task(send_events())
        except* starlette.websockets.WebSocketDisconnect:
            pass
