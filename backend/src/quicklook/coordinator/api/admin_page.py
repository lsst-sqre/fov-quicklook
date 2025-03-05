import asyncio

from fastapi import APIRouter

from quicklook.utils.http_request import http_request

from .generators import ctx

router = APIRouter()


@router.post("/kill")
async def kill():  # pragma: no cover
    async def kill_generator(g):
        try:
            await http_request('post', f'http://{g.host}:{g.port}/kill')
        except Exception:
            pass

    await asyncio.gather(*(kill_generator(g) for g in ctx().generators))
