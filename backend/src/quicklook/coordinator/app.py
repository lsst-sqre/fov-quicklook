from fastapi import FastAPI
from pydantic import BaseModel

from quicklook.comm.coordinator import router as comm_coordinator_router, lifespan as coordinator_lifespan
from quicklook.coordinator.create_quicklook import create_quicklook
from quicklook.job.job import Job
from quicklook.types import VisitName

app = FastAPI(lifespan=coordinator_lifespan)
app.include_router(comm_coordinator_router)


@app.get("/healthz")
async def route_healthz() -> dict[str, str]:
    return {"status": "ok"}


class CreateQuicklookRequest(BaseModel):
    visit: str


@app.post('/quicklooks')
async def route_create_quicklook(params: CreateQuicklookRequest):
    visit = VisitName(params.visit)
    await create_quicklook(Job(visit=visit))
