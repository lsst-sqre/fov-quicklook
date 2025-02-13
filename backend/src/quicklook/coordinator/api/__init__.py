from contextlib import asynccontextmanager

from fastapi import FastAPI

from quicklook.coordinator.quicklook import Quicklook
from quicklook.utils.http_request import http_request

from .generators import active_context, ctx
from .generators import router as context_router
from .healthz import router as healthz_router
from .quicklooks import router as quicklooks_router
from .podstatus import router as podstatus_router
import asyncio


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


@app.post("/kill")
async def kill():
    async def kill_generator(g):
        try:
            await http_request('post', f'http://{g.host}:{g.port}/kill')
        except Exception:
            pass

    await asyncio.gather(*(kill_generator(g) for g in ctx().generators))
