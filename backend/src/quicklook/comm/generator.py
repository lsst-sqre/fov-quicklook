"""
Generator側の通信モジュール。

Coordinatorに対して定期的に自身の存在を通知し、RPCエンドポイントを提供する。
Coordinatorとの疎通を定期的に確認し、失敗した場合は自プロセスを終了する。
"""

import asyncio
import quicklook.mylogging
import os
import signal
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager, contextmanager
from dataclasses import dataclass, field
from typing import Any

import aiohttp
from fastapi import APIRouter, HTTPException

from quicklook.comm.types import CoordinatorId, GeneratorId
from quicklook.config import config

from .types import GeneratorId, GeneratorRegistrationRequest, GeneratorRegistrationResponse

logger = quicklook.mylogging.getLogger(__name__)


router = APIRouter()

_shutdown_requested = False


@router.get("/comm/healthz")
async def generator_heartbeat(fail_for_test: bool = False):
    if config.environment == 'test' and fail_for_test:
        raise HTTPException(status_code=500, detail="Simulated failure for test")
    return {"status": "alive"}


@router.post("/comm/shutdown")
async def shutdown_generator():
    global _shutdown_requested
    _shutdown_requested = True
    logger.info(f"Shutdown requested for generator {self_generator_id()}")
    asyncio.create_task(_immediate_shutdown())
    return {"status": "shutting_down"}


_generator_id: GeneratorId | None = None
_coordinator_id: CoordinatorId | None = None


@asynccontextmanager
async def lifespan(app: Any) -> AsyncIterator[None]:
    global _generator_id
    _generator_id = GeneratorId(f'g-{uuid.uuid4().hex}')
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


def self_generator_id() -> GeneratorId:
    # 同じコンテナ内に2つのgeneratorがある時に
    # 作業ディレクトリがぶつからないようにするときなどに使う
    # 開発時にしか必要ないかもしれない
    if _generator_id is None:  # pragma: no cover
        raise RuntimeError(f"Generator ID is not set, pid={os.getpid()}")
    return GeneratorId(_generator_id)


@contextmanager
def set_generator_id_for_test():
    """Generator IDのコンテキストマネージャ。"""
    global _generator_id
    # assert config.environment == 'test' and _generator_id is None
    _generator_id = GeneratorId('generator_id_for_test')
    try:
        yield
    finally:
        _generator_id = None


async def _register_to_coordinator():
    global _coordinator_id

    registration_data = GeneratorRegistrationRequest(
        generator_id=self_generator_id(),
        port=config.generator_port,
        coordinator_id=_coordinator_id,
    )
    timeout = aiohttp.ClientTimeout(total=config.comm_heartbeat_timeout)
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(
                f"{config.coordinator_base_url}/comm/register",
                json=registration_data.model_dump(),
                timeout=timeout,
            ) as response:
                response.raise_for_status()
                response_data = await response.json()
                registration_response = GeneratorRegistrationResponse(**response_data)
                
                if _coordinator_id is None:
                    _coordinator_id = registration_response.coordinator_id
                    logger.info(f"Received coordinator ID: {_coordinator_id}")
                elif _coordinator_id != registration_response.coordinator_id:
                    logger.error(
                        f"Coordinator ID changed from {_coordinator_id} to {registration_response.coordinator_id}. "
                        "Coordinator has been restarted."
                    )
                    raise RuntimeError("Coordinator ID mismatch")
        except Exception:
            if config.dev_generator_required_coordinator_connection:  # pragma: no cover
                raise


async def _registration_loop():
    while True:
        if _shutdown_requested:
            logger.info("Registration loop stopped due to shutdown request")
            break
        await asyncio.sleep(config.comm_registration_interval)
        try:
            await _register_to_coordinator()
            continue
        except Exception as e:  # pragma: no cover
            logger.warning(f'Error occurred while registering generator: {e}')
            await _shutdown()


async def _immediate_shutdown():
    logger.info(f'Immediately shutting down generator {self_generator_id()}')
    await asyncio.sleep(0.1)
    os.kill(os.getpid(), signal.SIGINT)
    await asyncio.sleep(1)
    os.kill(os.getpid(), signal.SIGKILL)


async def _shutdown():  # pragma: no cover
    logger.error(f'Shutting down generator {self_generator_id()}')
    await asyncio.sleep(10)
    os.kill(os.getpid(), signal.SIGINT)
    await asyncio.sleep(10)
    os.kill(os.getpid(), signal.SIGKILL)


@dataclass
class GeneratorIdInitializer:
    # multiprocessingの子プロセスのためのinitializer

    generator_id: GeneratorId = field(default_factory=self_generator_id)

    @contextmanager
    def __call__(self):
        global _generator_id
        _generator_id = self.generator_id
        try:
            yield
        finally:  # pragma: no cover
            _generator_id = None
