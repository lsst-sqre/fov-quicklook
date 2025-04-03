import asyncio
import logging
import pickle

import starlette
import starlette.websockets
from fastapi import APIRouter, BackgroundTasks, WebSocket
from pydantic import BaseModel
from sqlalchemy import delete

from quicklook import storage
from quicklook.coordinator.api.generators import ctx
from quicklook.db import db_context
from quicklook.models import QuicklookRecord
from quicklook.types import GeneratorPod, Visit
from quicklook.utils.http_request import http_request
from quicklook.utils.websocket import safe_websocket

from ..quicklookjob.job_runner import job_runner

logger = logging.getLogger(f'uvicorn.{__name__}')
router = APIRouter()


class QuicklookCreate(BaseModel):
    visit: Visit


@router.post("/quicklooks")
async def create_quicklook(params: QuicklookCreate, background_tasks: BackgroundTasks):
    visit = params.visit
    background_tasks.add_task(job_runner.enqueue, visit)


@router.delete("/quicklooks/*")
async def delete_all_quicklooks():
    job_runner.clear()
    
    with db_context() as db:
        db.execute(delete(QuicklookRecord))
        db.commit()

    async def delete_generator(g: GeneratorPod):
        await http_request('delete', f'http://{g.host}:{g.port}/quicklooks/*')

    await asyncio.gather(*(delete_generator(g) for g in ctx().generators))
    await asyncio.to_thread(storage.clear_all)
    


@router.websocket("/quicklook-jobs/events.ws")
async def quicklook_events(
    ws: WebSocket,
):
    await ws.accept()
    async with safe_websocket(ws):

        async def send_events():
            async for events in job_runner.subscribe():
                await ws.send_bytes(pickle.dumps(events))

        try:
            async with asyncio.TaskGroup() as tg:
                tg.create_task(ws.receive_text())  # check connection
                tg.create_task(send_events())
        except* starlette.websockets.WebSocketDisconnect:
            pass
