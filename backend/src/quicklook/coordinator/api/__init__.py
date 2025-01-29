from contextlib import asynccontextmanager

from fastapi import FastAPI

from quicklook.coordinator.quicklook import Quicklook

from .generators import active_context
from .generators import router as context_router
from .healthz import router as healthz_router
from .quicklooks import router as quicklooks_router
from .podstatus import router as podstatus_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with active_context():
        with Quicklook.enable_subscription():
            yield


app = FastAPI(lifespan=lifespan)

app.include_router(healthz_router)
app.include_router(context_router)
app.include_router(quicklooks_router)
app.include_router(podstatus_router)
