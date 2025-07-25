from contextlib import asynccontextmanager

from fastapi import FastAPI

from quicklook.config import config
from quicklook.coordinator.housekeep import clear_imcomplete_quicklooks

from .generators import activate_context
from .generators import router as context_router
from .healthz import router as healthz_router
from .podstatus import router as podstatus_router
from .quicklooks import router as quicklooks_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    await clear_imcomplete_quicklooks()
    async with activate_context():
        yield


app = FastAPI(lifespan=lifespan)

app.include_router(healthz_router)
app.include_router(context_router)
app.include_router(quicklooks_router)
app.include_router(podstatus_router)


if config.admin_page:  # pragma: no cover
    from .admin_page import router as admin_page_router

    app.include_router(admin_page_router)

if config.environment == 'test':
    from .mutable_config_route import router as mutable_config_router

    app.include_router(mutable_config_router)
