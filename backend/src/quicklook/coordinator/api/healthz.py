import asyncio

import aiohttp
from fastapi import APIRouter
from pydantic import BaseModel

from quicklook.coordinator.api.generators import ctx
from quicklook.types import GeneratorPod
from quicklook.utils.timeit import timeit


class GeneratorHealth(BaseModel):
    pod: GeneratorPod
    status: str


router = APIRouter()


@router.get('/healthz')
async def healthz():
    return {'status': 'ok'}


@router.get('/ready', response_model=list[GeneratorHealth])
async def ready():
    async def generator_health(g: GeneratorPod) -> GeneratorHealth:
        with timeit(f'ready {g.host}:{g.port}'):
            async with aiohttp.ClientSession() as session:
                try:
                    async with session.get(
                        f'http://{g.host}:{g.port}/ready',
                        raise_for_status=True,
                        timeout=aiohttp.ClientTimeout(total=1),
                    ) as response:
                        response.raise_for_status()
                        return GeneratorHealth(pod=g, status='ok')
                except Exception as e:  # pragma: no cover
                    return GeneratorHealth(pod=g, status='ng')

    with timeit('ready'):
        return await asyncio.gather(*[generator_health(g) for g in ctx().generators])
