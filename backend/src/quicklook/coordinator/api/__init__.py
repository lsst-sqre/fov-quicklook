from contextlib import asynccontextmanager

from fastapi import FastAPI

from quicklook.config import config
from quicklook.coordinator.quicklookjob.job_pipeline import job_manager

from .admin_page import router as admin_page_router
from .generators import active_context
from .generators import router as context_router
from .healthz import router as healthz_router
from .podstatus import router as podstatus_router
from .quicklooks import router as quicklooks_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with active_context():
        async with job_manager.activate():
            yield


app = FastAPI(lifespan=lifespan)

app.include_router(healthz_router)
app.include_router(context_router)
app.include_router(quicklooks_router)
app.include_router(podstatus_router)
if config.admin_page:  # pragma: no cover
    app.include_router(admin_page_router)
