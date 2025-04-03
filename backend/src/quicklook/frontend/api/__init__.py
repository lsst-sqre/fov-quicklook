import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.routing import APIRoute

from quicklook.config import config
from quicklook.frontend.api.compression import setup_compression
from quicklook.frontend.api.remotejobs import RemoteQuicklookJobsWatcher
from quicklook.frontend.api.staticassets import setup_static_assets

from .get_fits_header import router as get_fits_header_router
from .get_tile import router as gettile_router
from .health import router as health_router
from .podstatus import router as pod_status_router
from .quicklooks import router as quicklooks_router
from .systeminfo import router as systeminfo_router
from .visits import router as visits_router
from .get_fits_file import router as get_fits_file_router
from .cache_entries import router as cache_entries_router
from .storage_explorer import router as storage_explorer_router

logger = logging.getLogger(f'uvicorn.{__name__}')


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with RemoteQuicklookJobsWatcher().activate():
        yield


app = FastAPI(lifespan=lifespan)

app.include_router(systeminfo_router, prefix=config.frontend_app_prefix)
app.include_router(health_router, prefix=config.frontend_app_prefix)
app.include_router(gettile_router, prefix=config.frontend_app_prefix)
app.include_router(get_fits_header_router, prefix=config.frontend_app_prefix)
app.include_router(quicklooks_router, prefix=config.frontend_app_prefix)
app.include_router(visits_router, prefix=config.frontend_app_prefix)
app.include_router(get_fits_file_router, prefix=config.frontend_app_prefix)


if config.admin_page:  # pragma: no cover
    app.include_router(pod_status_router, prefix=config.frontend_app_prefix)
    app.include_router(cache_entries_router, prefix=config.frontend_app_prefix)
    app.include_router(storage_explorer_router, prefix=config.frontend_app_prefix)

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
setup_compression(app, f'{config.frontend_app_prefix}/assets')
