import asyncio
import logging
import pickle
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any, AsyncIterator, Awaitable, Callable

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect

from quicklook.comm.coordinator import lifespan as coordinator_lifespan
from quicklook.comm.coordinator import router as comm_coordinator_router
from quicklook.coordinator.api.types import (
    CreateQuicklookRequest,
    JobStatusList,
    SharedStatusMessage,
    SharedStatusMessageJobSharedLargeStatus,
    SharedStatusMessageJobStatusList,
)
from quicklook.coordinator.create_quicklook import quicklook_pipeline
from quicklook.job.job import Job
from quicklook.types import VisitName
from quicklook.utils.broadcast import Broadcast
from quicklook.utils.websocket import run_until_disconnect, safe_websocket

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    global running_pipeline

    async with coordinator_lifespan(app):
        async with run_quicklook_pipeline() as running_pipeline:
            yield


app = FastAPI(lifespan=lifespan)
app.include_router(comm_coordinator_router)


@app.get("/healthz")
async def route_healthz():
    return


type JobDict = dict[VisitName, Job]


@app.post('/quicklooks')
async def route_create_quicklook(params: CreateQuicklookRequest):
    visit = VisitName(params.visit)
    await running_pipeline.push(visit)


def _job_status_list(jobs: JobDict) -> JobStatusList:
    return {visit: job.status for visit, job in jobs.items()}


@app.get('/quicklooks/*/status', response_model=JobStatusList)
async def route_quicklook_status():
    jobs = running_pipeline.jobs()
    return _job_status_list(jobs)


@app.websocket('/quicklooks/*/shared_status.ws')
async def ws_route_quicklook_shared_status(ws: WebSocket):
    async with safe_websocket(ws):

        async def send_progress():
            async for msg in running_pipeline.subscribe_shared_status():
                await ws.send_bytes(pickle.dumps(msg))

        await run_until_disconnect(ws, send_progress())


@asynccontextmanager
async def run_quicklook_pipeline():
    jobs: JobDict = {}
    broadcast = Broadcast[JobDict](4)
    shared_status_broadcast = Broadcast[SharedStatusMessage](4)

    async def notify(_: Job):
        broadcast.put(jobs)

    async def notify_shared_large_status(job: Job):
        msg = SharedStatusMessageJobSharedLargeStatus(
            visit=job.visit,
            data=job.shared_large_status,
        )
        shared_status_broadcast.put(msg)

    async def push(visit: VisitName) -> None:
        if visit in jobs:
            logger.info(f'Job for visit {visit} is already running')
            return
        job = Job(visit)
        job.watcher.on_change_status(on_status_change, which=lambda s: s.stage)
        job.watcher.on_change_status(notify)
        job.watcher.on_shared_large_status_change(notify_shared_large_status)
        jobs[visit] = job
        if ph.full():
            raise HTTPException(503)
        await ph.push(job)

    async def on_status_change(job: Job):
        async def _cleanup_delay():
            await asyncio.sleep(5)
            if job.visit in jobs:
                del jobs[job.visit]
                await notify(job)

        match job.status.stage:
            case 'ready':
                del jobs[job.visit]
            case 'error':
                asyncio.create_task(_cleanup_delay())

    async def subscribe_shared_status():
        job_status_queue: asyncio.Queue[SharedStatusMessage] = asyncio.Queue()
        
        async def forward_job_status():
            async for jobs_dict in broadcast.subscribe():
                msg = SharedStatusMessageJobStatusList(data=_job_status_list(jobs_dict))
                await job_status_queue.put(msg)
        
        async def forward_shared_large_status():
            async for msg in shared_status_broadcast.subscribe():
                await job_status_queue.put(msg)
        
        task1 = asyncio.create_task(forward_job_status())
        task2 = asyncio.create_task(forward_shared_large_status())
        
        try:
            while True:
                msg = await job_status_queue.get()
                yield msg
        finally:
            task1.cancel()
            task2.cancel()
            try:
                await task1
            except asyncio.CancelledError:
                pass
            try:
                await task2
            except asyncio.CancelledError:
                pass

    async with quicklook_pipeline().run() as ph:
        async with broadcast.activate():
            async with shared_status_broadcast.activate():
                yield RunningPipeline(
                    push=push,
                    jobs=lambda: jobs,
                    subscribe_progress=broadcast.subscribe,
                    subscribe_shared_status=subscribe_shared_status,
                )


@dataclass
class RunningPipeline:
    push: Callable[[VisitName], Awaitable[None]]
    jobs: Callable[[], JobDict]
    subscribe_progress: Callable[[], AsyncIterator[JobDict]]
    subscribe_shared_status: Callable[[], AsyncIterator[SharedStatusMessage]]
