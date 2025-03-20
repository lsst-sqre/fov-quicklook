import asyncio

import aiohttp
from fastapi import APIRouter
from pydantic import BaseModel

from quicklook.coordinator.api.generators import ctx
from quicklook.mutableconfig import update_mutable_config
from quicklook.types import GeneratorPod
from quicklook.utils.timeit import timeit

router = APIRouter()


class MutableConfigUpdate(BaseModel):
    new: dict


@router.post('/mutable-config')
async def update_mutable_config_route(params: MutableConfigUpdate):
    update_mutable_config(params.new)

    async def update_generator_mutable_config(g: GeneratorPod):
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f'http://{g.host}:{g.port}/mutable-config',
                raise_for_status=True,
                timeout=aiohttp.ClientTimeout(total=1),
                json={'new': params.new},
            ) as response:
                pass

    return await asyncio.gather(*[update_generator_mutable_config(g) for g in ctx().generators])
