import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request

import quicklook.mylogging

from quicklook.config import config
from quicklook.frontend.api.compression import setup_compression
from quicklook.frontend.api.staticassets import setup_static_assets
from quicklook.frontend.api.use_route_names_as_operation_ids import use_route_names_as_operation_ids
from quicklook.frontend.comm import lifespan as comm_lifespan
from quicklook.utils.http_client import managed_session
from quicklook.utils.system_status import get_memory_current

from .admin import router as admin_router
from .get_fits_file import router as get_fits_file_router
from .get_fits_header import router as get_fits_header_router
from .get_tile import router as gettile_router
from .health import router as health_router
from .quicklooks import lifespan as quicklook_lifespan
from .quicklooks import router as quicklooks_router
from .storage_explorer import router as storage_explorer_router
from .systeminfo import router as systeminfo_router
from .status import router as status_router
from .visits import router as visits_router
from .cache_entries import router as cache_entries_router

logger = quicklook.mylogging.getLogger(__name__)


def _should_log_frontend_request(path: str) -> bool:
    prefix = config.frontend_app_prefix
    return (
        path.startswith(f"{prefix}/assets/")
        or path.startswith(f"{prefix}/visits/")
        or path == f"{prefix}/api/status"
        or (
            path.startswith(f"{prefix}/api/quicklooks/")
            and (
                "quicklook_metadata" in path
                or path.endswith("/vote")
                or path.endswith("/unvote")
            )
        )
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    from quicklook.revision import GIT_REVISION
    logger.info("Frontend starting, revision=%s", GIT_REVISION)

    async with managed_session():
        async with quicklook_lifespan(app):
            async with comm_lifespan(app):
                yield


app = FastAPI(lifespan=lifespan)


@app.middleware("http")
async def log_frontend_memory(request: Request, call_next):
    path = request.url.path
    if not _should_log_frontend_request(path):
        return await call_next(request)

    rss_before = get_memory_current()
    started_at = time.monotonic()
    response = await call_next(request)
    rss_after = get_memory_current()
    logger.info(
        "Frontend request path=%s method=%s status=%s rss_before=%d rss_after=%d rss_delta=%d duration_ms=%d content_length=%s",
        path,
        request.method,
        response.status_code,
        rss_before,
        rss_after,
        rss_after - rss_before,
        int((time.monotonic() - started_at) * 1000),
        response.headers.get("content-length", "-"),
    )
    return response

app.include_router(systeminfo_router, prefix=config.frontend_app_prefix)
app.include_router(status_router, prefix=config.frontend_app_prefix)
app.include_router(health_router, prefix=config.frontend_app_prefix)
app.include_router(gettile_router, prefix=config.frontend_app_prefix)
app.include_router(get_fits_header_router, prefix=config.frontend_app_prefix)
app.include_router(quicklooks_router, prefix=config.frontend_app_prefix)
app.include_router(visits_router, prefix=config.frontend_app_prefix)
app.include_router(get_fits_file_router, prefix=config.frontend_app_prefix)

if config.admin_page:  # pragma: no cover
    app.include_router(admin_router, prefix=config.frontend_app_prefix)
    app.include_router(cache_entries_router, prefix=config.frontend_app_prefix)
    app.include_router(storage_explorer_router, prefix=config.frontend_app_prefix)


setup_static_assets(app)
use_route_names_as_operation_ids(app)
setup_compression(app, f'{config.frontend_app_prefix}/assets')
