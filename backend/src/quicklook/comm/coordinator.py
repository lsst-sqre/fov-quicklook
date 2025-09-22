"""
Coordinator側の通信モジュール。

GeneratorからのRegistration要求を受け付け、利用可能なGeneratorのリストを管理する。
定期的にGeneratorにHeartbeatを送信し、応答がないGeneratorをリストから削除する。
"""

import asyncio
import logging
import traceback
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

import aiohttp
from fastapi import APIRouter, Request

from quicklook.config import config

from .types import GeneratorInfo, GeneratorRegistrationRequest

logger = logging.getLogger(__name__)
_available_generators: dict[str, GeneratorInfo] = {}


router = APIRouter()


@router.post("/register")
async def register_generator(
    request: Request,
    registration_data: GeneratorRegistrationRequest,
):
    client_host = request.client.host if request.client else "127.0.0.1"
    generator_info = GeneratorInfo(
        host=client_host,
        port=registration_data.port,
        max_concurrent_jobs=registration_data.max_concurrent_jobs,
    )
    generator_id = f"{generator_info.host}:{generator_info.port}"
    _available_generators[generator_id] = generator_info
    logger.info(f'Available generators: {list(_available_generators.keys())}')


if config.environment == 'test':  # pragma: no branch

    @router.get("/generators")
    async def list_generators():
        return {"generators": get_available_generators()}

    @router.post("/trigger-heartbeat")
    async def trigger_heartbeat(fail_for_test: bool = False):
        await _heartbeat_check(fail_for_test=fail_for_test)
        return {"status": "ok"}


@asynccontextmanager
async def lifespan(app: Any) -> AsyncIterator[None]:
    heartbeat_task = asyncio.create_task(_heartbeat_checker_loop())
    try:
        yield
    finally:
        heartbeat_task.cancel()
        try:
            await heartbeat_task
        except asyncio.CancelledError:
            pass


def get_available_generators() -> list[GeneratorInfo]:
    return list(_available_generators.values())


async def _heartbeat_checker_loop():
    while True:
        await asyncio.sleep(config.comm_heartbeat_interval)
        await _heartbeat_check()  # pragma: no cover


async def _heartbeat_check(*, fail_for_test: bool = False):
    timeout = aiohttp.ClientTimeout(total=config.comm_heartbeat_timeout)

    async def check_generator(
        session: aiohttp.ClientSession,
        generator_id: str,
        generator_info: GeneratorInfo,
    ) -> str | None:
        url = f"{generator_info.url}/heartbeat?fail_for_test={str(fail_for_test).lower()}"
        try:
            await session.get(url, raise_for_status=True)
        except:
            traceback.print_exc()
            return generator_id

    async with aiohttp.ClientSession(timeout=timeout) as session:
        tasks = [check_generator(session, generator_id, generator_info) for generator_id, generator_info in _available_generators.items()]
        results = await asyncio.gather(*tasks)
        to_remove = [gid for gid in results if gid is not None]

    # 応答がなかったGeneratorを削除
    for generator_id in to_remove:
        if generator_id in _available_generators:  # pragma: no branch
            del _available_generators[generator_id]
            logger.info(f"Generator removed due to heartbeat failure: {generator_id}")
