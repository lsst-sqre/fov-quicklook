from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any, AsyncIterator, Callable

from fastapi import FastAPI, HTTPException, WebSocket
from pydantic import BaseModel

from quicklook.comm.coordinator import lifespan as coordinator_lifespan
from quicklook.comm.coordinator import router as comm_coordinator_router
from quicklook.coordinator.create_quicklook import quicklook_pipeline
from quicklook.job.job import Job
from quicklook.job.status_printer import JobStatusPrinter
from quicklook.types import VisitName
from quicklook.utils.broadcast import Broadcast
from quicklook.utils.websocket import safe_websocket


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


class CreateQuicklookRequest(BaseModel):
    visit: str


@app.post('/quicklooks')
async def route_create_quicklook(params: CreateQuicklookRequest):
    visit = VisitName(params.visit)
    await running_pipeline.push(visit)


type JobStatusList = dict[VisitName, Job]


@app.get('/quicklooks/*/status', response_model=JobStatusList)
async def route_quicklook_status():
    # これは使わないかも。
    return running_pipeline.jobs()


@app.websocket('/quicklooks/*/status.ws')
async def ws_route_quicklook_status(ws: WebSocket):
    await ws.accept()
    async with safe_websocket(ws):
        async for status in running_pipeline.subscribe():
            await ws.send_json(status)


@asynccontextmanager
async def run_quicklook_pipeline():
    jobs: JobStatusList = {}
    broadcast = Broadcast(4)

    printer = JobStatusPrinter()

    async def notify(job: Job):
        printer(job.status)
        broadcast.put(job)

    async def push(visit: VisitName) -> None:
        if visit in jobs:
            return
        job = Job(visit)
        job.status.on_change(on_status_change, which=lambda s: s.stage)
        job.status.on_change(notify)
        jobs[visit] = job
        if ph.full():
            raise HTTPException(503)
        await ph.push(job)

    async def on_status_change(job: Job):
        if job.status.stage == 'done':
            printer.flush()
            del jobs[job.visit]

    async with quicklook_pipeline().run() as ph:
        async with broadcast.activate():
            try:
                yield RunningPipeline(push, broadcast.subscribe, lambda: jobs)
            finally:
                ph.cancel()


@dataclass
class RunningPipeline:
    push: Any
    subscribe: Callable[[], AsyncIterator[JobStatusList]]
    jobs: Callable[[], JobStatusList]
