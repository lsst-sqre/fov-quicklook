import asyncio
import logging
import pickle
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any, AsyncIterator, Awaitable, Callable

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect

from quicklook.comm.coordinator import lifespan as coordinator_lifespan
from quicklook.comm.coordinator import router as comm_coordinator_router
from quicklook.coordinator.api.types import CreateQuicklookRequest, JobStatusList
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


@app.websocket('/quicklooks/*/status.ws')
async def ws_route_quicklook_status(ws: WebSocket):
    async with safe_websocket(ws):

        async def send_progress():
            async for jobs in running_pipeline.subscribe_progress():
                await ws.send_bytes(pickle.dumps(_job_status_list(jobs)))

        await run_until_disconnect(ws, send_progress())


@asynccontextmanager
async def run_quicklook_pipeline():
    jobs: JobDict = {}
    broadcast = Broadcast[JobDict](4)

    async def notify(_: Job):
        broadcast.put(jobs)

    async def push(visit: VisitName) -> None:
        if visit in jobs:
            logger.info(f'Job for visit {visit} is already running')
            return
        job = Job(visit)
        job.watcher.on_change(on_status_change, which=lambda s: s.stage)
        job.watcher.on_change(notify)
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
            case 'done':
                del jobs[job.visit]
            case 'error':
                asyncio.create_task(_cleanup_delay())

    async with quicklook_pipeline().run() as ph:
        async with broadcast.activate():
            yield RunningPipeline(
                push=push,
                jobs=lambda: jobs,
                subscribe_progress=broadcast.subscribe,
            )


@dataclass
class RunningPipeline:
    push: Callable[[VisitName], Awaitable[None]]
    jobs: Callable[[], JobDict]
    subscribe_progress: Callable[[], AsyncIterator[JobDict]]
