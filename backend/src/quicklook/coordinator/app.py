import asyncio
from contextlib import asynccontextmanager
from functools import lru_cache
import itertools
from dataclasses import dataclass, field
from typing import TypeVar

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from quicklook.comm.coordinator import lifespan as coordinator_lifespan
from quicklook.comm.coordinator import router as comm_coordinator_router
from quicklook.config import config
from quicklook.coordinator.create_quicklook import create_quicklook, quicklook_pipeline
from quicklook.job.job_status_printer import JobStatusPrinter
from quicklook.job.job import Job
from quicklook.types import VisitName
from quicklook.utils.pipeline import Pipeline, Stage


@asynccontextmanager
async def lifespan(app: FastAPI):
    global quicklook_pipeline_handle
    async with coordinator_lifespan(app):
        async with pipeline().run() as quicklook_pipeline_handle:
            try:
                yield
            finally:
                quicklook_pipeline_handle.cancel()


app = FastAPI(lifespan=lifespan)
app.include_router(comm_coordinator_router)


@app.get("/healthz")
async def route_healthz() -> dict[str, str]:
    return {"status": "ok"}


class CreateQuicklookRequest(BaseModel):
    visit: str


@app.post('/quicklooks')
async def route_create_quicklook(params: CreateQuicklookRequest):
    req = _QuicklookRequest.from_visit(VisitName(params.visit))
    if quicklook_pipeline_handle.full():
        raise HTTPException(503)
    await quicklook_pipeline_handle.push(req)


@dataclass
class _QuicklookRequest:
    _seq = itertools.count()

    visit: VisitName
    vote: int = 1
    seq: int = field(default_factory=lambda: next(_QuicklookRequest._seq))

    @classmethod
    @lru_cache(config.pipeline_queue_size)
    def from_visit(cls, visit: VisitName):
        return cls(visit=visit)

    def __hash__(self):
        return hash(self.visit)


def pipeline():
    # 最初のステージはリクエストの重複を省き、優先度の高いリクエストを選択する
    # 次のステージは行列長の制限

    def item_picker(reqs: list[_QuicklookRequest]):
        # ここはpushされるとすぐに呼ばれる
        # reqsを破壊的に更新し、優先度の高いリクエストを選択する
        reqs.sort(key=lambda x: (-x.vote, x.seq))
        return reqs.pop(0)

    async def noop(req: _QuicklookRequest):
        return req

    async def make_job(req: _QuicklookRequest):
        job = Job(req.visit)
        printer = JobStatusPrinter()
        job.status.on_change(lambda _: printer(job.status))
        return job

    return (
        Pipeline(
            Stage(noop, item_picker=item_picker),
        )
        .append(
            Stage(make_job, queue_capacity=config.pipeline_queue_size),
        )
        .concat(quicklook_pipeline())
    )
