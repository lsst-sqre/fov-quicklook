"""
Generator側の通信モジュール。

Coordinatorに対して定期的に自身の存在を通知し、RPCエンドポイントを提供する。
Coordinatorとの疎通を定期的に確認し、失敗した場合は自プロセスを終了する。
"""

import asyncio
import logging
import os
import signal
import traceback
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

import aiohttp
from fastapi import APIRouter

from quicklook.config import config

from .types import GeneratorRegistrationRequest

logger = logging.getLogger(__name__)


router = APIRouter()


@router.get("/heartbeat")
async def generator_heartbeat(fail_for_test: bool = False):
    if config.environment == 'test' and fail_for_test:
        raise Exception("Simulated heartbeat failure")
    return {"status": "alive"}


@router.post("/rpc")
async def rpc_endpoint(): ...


@asynccontextmanager
async def lifespan(app: Any) -> AsyncIterator[None]:
    await _register_to_coordinator()
    registration_task = asyncio.create_task(_registration_loop())
    try:
        yield
    finally:
        registration_task.cancel()
        try:
            await registration_task
        except asyncio.CancelledError:
            pass


async def _register_to_coordinator():
    registration_data = GeneratorRegistrationRequest(
        port=config.generator_port,
        max_concurrent_jobs=config.comm_generator_max_concurrent_jobs,
    )
    timeout = aiohttp.ClientTimeout(total=config.comm_heartbeat_timeout)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        await session.post(
            f"{config.coordinator_base_url}/register",
            json=registration_data.model_dump(),
            raise_for_status=True,
        )


async def _registration_loop():
    try:
        while True:
            await _register_to_coordinator()
            await asyncio.sleep(config.comm_registration_interval)
    except Exception as e:  # pragma: no cover
        traceback.print_exc()
        await _shutdown()


async def _shutdown():  # pragma: no cover
    await asyncio.sleep(10)  # 繰り返しの再起動を防ぐために少し待つ
    os.kill(os.getpid(), signal.SIGINT)
    # さらに待って強制終了
    await asyncio.sleep(10)
    os.kill(os.getpid(), signal.SIGKILL)
