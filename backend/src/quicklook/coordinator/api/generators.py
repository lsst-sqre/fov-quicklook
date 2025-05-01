import asyncio
import contextlib
import logging
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from functools import cache

import aiohttp
from fastapi import APIRouter, Request
from pydantic import BaseModel

from quicklook.config import config
from quicklook.types import GeneratorPod
from quicklook.utils.asynctask import cancel_at_exit

logger = logging.getLogger('uvicorn')


@dataclass
class CoordinatorContext:
    generators: list[GeneratorPod] = field(default_factory=list)

    @asynccontextmanager
    async def activate(self):
        with cancel_at_exit(asyncio.create_task(self._periodic_task())):
            yield

    async def _periodic_task(self):
        while True:
            await self._check_generators()
            await asyncio.sleep(config.heartbeat_interval)

    def _print_generators(self):
        logger.info(f'generators: {[f"{g.host}:{g.port}" for g in self.generators]}')

    # generatorsの状態を確認
    async def _check_generators(self):
        async def check_generator(generator: GeneratorPod):  # pragma: no cover
            async with aiohttp.ClientSession() as session:
                try:
                    async with session.get(
                        f'http://{generator.host}:{generator.port}/healthz',
                        timeout=aiohttp.ClientTimeout(total=1),
                        raise_for_status=True,
                    ):
                        pass
                except Exception as e:
                    logger.info(f'generator {generator.host}:{generator.port} is not reachable: {e}')
                    self.generators.remove(generator)
                    self._print_generators()

        await asyncio.gather(*[check_generator(generator) for generator in self.generators], return_exceptions=True)

    def register_generator(self, generator: GeneratorPod):
        if generator not in self.generators:  # pragma: no branch
            logger.info(f'generator {generator.host}:{generator.port} is registered')
            self.generators.append(generator)
            self._print_generators()


@cache
def ctx():
    return CoordinatorContext()


def get_generators():
    return ctx().generators


@contextlib.asynccontextmanager
async def activate_context():
    async with ctx().activate():
        yield ctx()


class RegisterGeneratorRequest(BaseModel):
    port: int


router = APIRouter()


@router.post("/register_generator")
async def register_generator(params: RegisterGeneratorRequest, request: Request):
    ctx().register_generator(
        GeneratorPod(
            host=request.client.host,  # type: ignore
            port=params.port,
        )
    )
