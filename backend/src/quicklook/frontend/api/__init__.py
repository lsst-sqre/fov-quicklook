import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.routing import APIRoute

from quicklook.config import config
from quicklook.coordinator.quicklook import Quicklook
from quicklook.frontend.api.remotequicklook import RemoteQuicklookWather
from quicklook.frontend.api.staticassets import setup_static_assets

from .get_tile import router as gettile_router
from .get_fits_header import router as get_fits_header_router
from .health import router as health_router
from .podstatus import router as pod_status_router
from .systeminfo import router as systeminfo_router
from .quicklooks import router as quicklooks_router
from .visits import router as visits_router

logger = logging.getLogger(f'uvicorn.{__name__}')


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with RemoteQuicklookWather().activate():
        with Quicklook.enable_subscription():
            yield


app = FastAPI(lifespan=lifespan)

app.include_router(systeminfo_router, prefix=config.frontend_app_prefix)
app.include_router(health_router, prefix=config.frontend_app_prefix)
app.include_router(gettile_router, prefix=config.frontend_app_prefix)
app.include_router(get_fits_header_router, prefix=config.frontend_app_prefix)
app.include_router(quicklooks_router, prefix=config.frontend_app_prefix)
app.include_router(visits_router, prefix=config.frontend_app_prefix)

if config.admin_page:
    app.include_router(pod_status_router, prefix=config.frontend_app_prefix)

setup_static_assets(app)


def use_route_names_as_operation_ids(app: FastAPI) -> None:
    """
    https://fastapi.tiangolo.com/advanced/path-operation-advanced-configuration/

    Simplify operation IDs so that generated API clients have simpler function
    names.

    Should be called only after all routes have been added.
    """
    for route in app.routes:
        if isinstance(route, APIRoute):
            route.operation_id = route.name  # in this case, 'read_items'


use_route_names_as_operation_ids(app)
