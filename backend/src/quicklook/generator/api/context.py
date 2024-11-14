import asyncio
import logging
from contextlib import asynccontextmanager

import aiohttp

from quicklook.config import config
from quicklook.utils.asynctask import cancel_at_exit


class GeneratorContext:
    @asynccontextmanager
    async def activate(self, port: int):
        self._port = port
        with cancel_at_exit(asyncio.create_task(self._watch_coordinator())):
            yield

    async def _watch_coordinator(self):
        while True:
            try:
                await self._register()
            except Exception as e:  # pragma: no cover
                pass
                # logging.error(f'failed to register generator: {e}')
            await asyncio.sleep(config.heartbeat_interval)

    async def _register(self):
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f'{config.coordinator_base_url}/register_generator',
                json={
                    'port': self._port,
                },
                raise_for_status=True,
            ):
                pass
