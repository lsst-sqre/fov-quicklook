import asyncio
import logging
import pickle

import starlette
import starlette.websockets
from fastapi import APIRouter, BackgroundTasks, WebSocket
from pydantic import BaseModel
from sqlalchemy import delete

from quicklook.db import db_context
from quicklook.models import QuicklookRecord
from quicklook.types import Visit
from quicklook.utils.websocket import safe_websocket

from ..quicklookjob.job_pipeline import job_manager

logger = logging.getLogger(f'uvicorn.{__name__}')
router = APIRouter()


class QuicklookCreate(BaseModel):
    visit: Visit
    no_transfer: bool = False


@router.post("/quicklooks")
async def create_quicklook(params: QuicklookCreate):
    visit = params.visit
    await job_manager.enqueue(visit, no_transfer=params.no_transfer)


@router.delete("/quicklooks/*")
async def delete_all_quicklooks():
    with db_context() as db:
        db.execute(delete(QuicklookRecord))
        db.commit()
    await job_manager.clear()


@router.websocket("/quicklook-jobs/events.ws")
async def quicklook_events(
    ws: WebSocket,
):
    await ws.accept()
    async with safe_websocket(ws):

        async def send_events():
            async for events in job_manager.subscribe():
                await ws.send_bytes(pickle.dumps(events))

        try:
            async with asyncio.TaskGroup() as tg:
                tg.create_task(ws.receive_text())  # check connection
                tg.create_task(send_events())
        except* starlette.websockets.WebSocketDisconnect:
            pass
