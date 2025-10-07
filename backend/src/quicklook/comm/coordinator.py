"""
Coordinator側の通信モジュール。

GeneratorからのRegistration要求を受け付け、利用可能なGeneratorのリストを管理する。
定期的にGeneratorにHeartbeatを送信し、応答がないGeneratorをリストから削除する。
"""

import asyncio
import logging
import traceback
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

import aiohttp
from fastapi import APIRouter, Request, HTTPException

from quicklook.config import config

from .types import (
    CoordinatorId,
    GeneratorId,
    GeneratorInfo,
    GeneratorRegistrationRequest,
    GeneratorRegistrationResponse,
)

logger = logging.getLogger(__name__)
_available_generators: dict[GeneratorId, GeneratorInfo] = {}
_coordinator_id: CoordinatorId | None = None


router = APIRouter()


@router.post("/comm/register")
async def register_generator(
    request: Request,
    registration_data: GeneratorRegistrationRequest,
) -> GeneratorRegistrationResponse:
    if _coordinator_id is None:
        raise HTTPException(status_code=500, detail="Coordinator ID not initialized")
    
    if registration_data.coordinator_id is not None:
        if registration_data.coordinator_id != _coordinator_id:
            raise HTTPException(
                status_code=409,
                detail="Coordinator ID mismatch"
            )
    
    client_host = request.client.host if request.client else "127.0.0.1"
    generator_info = GeneratorInfo(
        id=registration_data.generator_id,
        host=client_host,
        port=registration_data.port,
    )
    if registration_data.generator_id not in _available_generators:
        _available_generators[registration_data.generator_id] = generator_info
        logger.info(f'Available generators: {_available_generators.values()}')
    
    return GeneratorRegistrationResponse(coordinator_id=_coordinator_id)


@router.get("/comm/healthz")
async def health_check():
    return {"status": "ok"}


if config.environment == 'test':  # pragma: no branch

    @router.get("/comm/generators")
    async def list_generators():
        return {"generators": get_available_generators()}

    @router.post("/comm/trigger-heartbeat")
    async def trigger_heartbeat(fail_for_test: bool = False):
        await _heartbeat_check(fail_for_test=fail_for_test)
        return {"status": "ok"}


@asynccontextmanager
async def lifespan(app: Any) -> AsyncIterator[None]:
    global _coordinator_id
    _coordinator_id = CoordinatorId(f'c-{uuid.uuid4().hex}')
    logger.info(f"Coordinator ID: {_coordinator_id}")
    heartbeat_task = asyncio.create_task(_heartbeat_checker_loop())
    try:
        yield
    finally:
        heartbeat_task.cancel()
        try:
            await heartbeat_task
        except asyncio.CancelledError:
            pass


def get_available_generators() -> dict[GeneratorId, GeneratorInfo]:
    return _available_generators


def remove_generator(generator_info: GeneratorInfo) -> None:
    if generator_info.id in _available_generators:  # pragma: no branch
        del _available_generators[generator_info.id]
        logger.info(f"Generator removed: {generator_info.id}")


async def _heartbeat_checker_loop():
    while True:
        await asyncio.sleep(config.comm_heartbeat_interval)
        await _heartbeat_check()  # pragma: no cover


async def _heartbeat_check(*, fail_for_test: bool = False):
    timeout = aiohttp.ClientTimeout(total=config.comm_heartbeat_timeout)

    async def check_generator(
        generator_info: GeneratorInfo,
    ) -> GeneratorInfo | None:
        url = f"{generator_info.url}/comm/healthz"
        if fail_for_test:
            url += f"?fail_for_test={str(fail_for_test).lower()}"
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url, timeout=timeout) as response:
                    response.raise_for_status()
            except Exception as e:
                logger.warning(f"Health check failed for {generator_info.id}: {e}")
                return generator_info

    tasks = [check_generator(generator_info) for generator_info in _available_generators.values()]
    results = await asyncio.gather(*tasks)
    to_remove = [gid for gid in results if gid is not None]

    for generator_info in to_remove:
        remove_generator(generator_info)
