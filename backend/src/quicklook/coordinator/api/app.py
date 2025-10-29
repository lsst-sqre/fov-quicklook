import asyncio
import pickle
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Annotated, AsyncIterator, Awaitable, Callable

from fastapi import Depends, FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy import select

import quicklook.mylogging
from quicklook.comm.coordinator import lifespan as coordinator_lifespan
from quicklook.comm.coordinator import router as comm_coordinator_router
from quicklook.coordinator.api.deps import dep_visit_name
from quicklook.coordinator.api.status import router as status_router
from quicklook.coordinator.api.types import (
    CreateQuicklookRequest,
    JobStatusList,
    SharedStatusMessage,
    SharedStatusMessageJobSharedLargeStatus,
    SharedStatusMessageJobStatusList,
)
from quicklook.coordinator.create_quicklook import quicklook_pipeline
from quicklook.coordinator.housekeeping import cleanup_at_startup
from quicklook.db import Quicklook, get_db_session
from quicklook.job.job import Job
from quicklook.types import VisitName
from quicklook.utils.broadcast import Broadcast
from quicklook.utils.websocket import run_until_disconnect, safe_websocket

logger = quicklook.mylogging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    global running_pipeline

    await cleanup_at_startup()

    async with coordinator_lifespan(app):
        async with run_quicklook_pipeline() as running_pipeline:
            yield


app = FastAPI(lifespan=lifespan)
app.include_router(comm_coordinator_router)
app.include_router(status_router)


@app.get("/healthz")
async def route_healthz():
    return


type JobDict = dict[VisitName, Job]


@app.post('/quicklooks')
async def route_create_quicklook(params: CreateQuicklookRequest):
    visit = VisitName(params.visit)

    async with get_db_session() as session:
        result = await session.execute(select(Quicklook).where(Quicklook.visit_name == visit))
        quicklook = result.scalar_one_or_none()

        if quicklook is not None:
            logger.info(f'Quicklook for visit {visit} already exists in DB')
            return

    await running_pipeline.push(visit)


def _job_status_list(jobs: JobDict) -> JobStatusList:
    return {visit: job.status for visit, job in jobs.items()}


@app.get('/quicklooks/*/status', response_model=JobStatusList)
async def route_quicklook_status():
    jobs = running_pipeline.jobs()
    return _job_status_list(jobs)


def _log_all_user_counts(jobs: JobDict):
    """すべてのジョブのvisit_nameとuser_countをログ出力"""
    entries = [(str(visit), job.priority.user_count) for visit, job in jobs.items()]
    if entries:
        entries_str = ", ".join(f"{visit}:{count}" for visit, count in entries)
        logger.info(f"All jobs user_count: {entries_str}")
    else:
        logger.info("All jobs user_count: (no jobs)")


@app.post('/quicklooks/{visit_name}/vote')
async def route_vote_quicklook(visit: Annotated[VisitName, Depends(dep_visit_name)]):
    jobs = running_pipeline.jobs()
    if visit not in jobs:
        return {"user_count": 0}
    
    job = jobs[visit]
    priority = job.priority
    priority.user_count += 1
    
    from quicklook.db import Access, Quicklook, get_db_session
    from datetime import datetime
    from sqlalchemy import select
    async with get_db_session() as session:
        result = await session.execute(select(Quicklook).where(Quicklook.visit_name == visit))
        quicklook = result.scalar_one_or_none()
        if quicklook is not None:
            access = Access(visit_name=visit, accessed_at=datetime.now())
            session.add(access)
            await session.commit()
    
    _log_all_user_counts(jobs)
    
    return {"user_count": priority.user_count}


@app.post('/quicklooks/{visit_name}/unvote')
async def route_unvote_quicklook(visit: Annotated[VisitName, Depends(dep_visit_name)]):
    jobs = running_pipeline.jobs()
    if visit not in jobs:
        return {"user_count": 0}
    
    job = jobs[visit]
    priority = job.priority
    if priority.user_count > 0:
        priority.user_count -= 1
    
    _log_all_user_counts(jobs)
    
    return {"user_count": priority.user_count}


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
    broadcast = Broadcast[SharedStatusMessage]()

    async def notify_progress(_: Job):
        broadcast.put(SharedStatusMessageJobStatusList(data=_job_status_list(jobs)))

    async def notify_shared_large_status(job: Job):
        msg = SharedStatusMessageJobSharedLargeStatus(
            visit=job.visit,
            data=job.shared_large_status,
        )
        broadcast.put(msg)

    async def push(visit: VisitName) -> None:
        if visit in jobs:
            logger.info(f'Job for visit {visit} is already running')
            return
        job = Job(visit)
        job.watcher.on_change_status(notify_progress)
        job.watcher.on_change_status(on_status_change, which=lambda s: s.stage)
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
                await notify_progress(job)

        match job.status.stage:
            case 'ready':
                del jobs[job.visit]
                await notify_progress(job)
            case 'error':
                asyncio.create_task(_cleanup_delay())

    async with quicklook_pipeline().run() as ph:
        async with broadcast.activate():
            yield RunningPipeline(
                push=push,
                jobs=lambda: jobs,
                subscribe_shared_status=broadcast.subscribe,
            )


@dataclass
class RunningPipeline:
    push: Callable[[VisitName], Awaitable[None]]
    jobs: Callable[[], JobDict]
    subscribe_shared_status: Callable[[], AsyncIterator[SharedStatusMessage]]
