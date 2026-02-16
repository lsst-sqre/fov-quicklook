"""
Coordinator側の通信モジュール。

GeneratorからのRegistration要求を受け付け、利用可能なGeneratorのリストを管理する。
定期的にGeneratorにHeartbeatを送信し、応答がないGeneratorをリストから削除する。
"""

import asyncio
import quicklook.mylogging
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any, Callable

import aiohttp
from fastapi import APIRouter, Request, HTTPException

from quicklook.config import config
from quicklook.utils.http_client import get_session, managed_session

from .types import (
    CoordinatorId,
    GeneratorId,
    GeneratorInfo,
    GeneratorRegistrationRequest,
    GeneratorRegistrationResponse,
)

logger = quicklook.mylogging.getLogger(__name__)


class CoordinatorRegistry:
    """
    Coordinator側のGenerator登録状態を管理するクラス。

    グローバル変数だったGenerator一覧・コールバック・Coordinator IDを集約し、
    テスト時にインスタンスを差し替えられるようにする。
    """

    def __init__(self) -> None:
        self._available_generators: dict[GeneratorId, GeneratorInfo] = {}
        self._coordinator_id: CoordinatorId | None = None
        self._on_generator_registered_callbacks: list[Callable] = []
        self._on_generator_removed_callbacks: list[Callable] = []

    @property
    def coordinator_id(self) -> CoordinatorId | None:
        return self._coordinator_id

    @coordinator_id.setter
    def coordinator_id(self, value: CoordinatorId | None) -> None:
        self._coordinator_id = value

    @property
    def available_generators(self) -> dict[GeneratorId, GeneratorInfo]:
        return self._available_generators

    def add_on_generator_registered_callback(self, callback: Callable) -> None:
        self._on_generator_registered_callbacks.append(callback)

    def remove_on_generator_registered_callback(self, callback: Callable) -> None:
        try:
            self._on_generator_registered_callbacks.remove(callback)
        except ValueError:
            pass

    def add_on_generator_removed_callback(self, callback: Callable) -> None:
        self._on_generator_removed_callbacks.append(callback)

    def remove_on_generator_removed_callback(self, callback: Callable) -> None:
        try:
            self._on_generator_removed_callbacks.remove(callback)
        except ValueError:
            pass

    def register_generator(self, generator_info: GeneratorInfo) -> None:
        if generator_info.id not in self._available_generators:
            self._available_generators[generator_info.id] = generator_info
            logger.debug(f'Available generators: {self._available_generators.values()}')
            for callback in self._on_generator_registered_callbacks:
                try:
                    callback(generator_info)
                except Exception as e:
                    logger.warning(f"Generator registration callback failed: {e}")

    def remove_generator(self, generator_info: GeneratorInfo) -> None:
        if generator_info.id in self._available_generators:  # pragma: no branch
            del self._available_generators[generator_info.id]
            logger.info(f"Generator removed: {generator_info.id}")
            for callback in self._on_generator_removed_callbacks:
                try:
                    callback(generator_info)
                except Exception as e:
                    logger.warning(f"Generator removed callback failed: {e}")


_registry = CoordinatorRegistry()


def get_registry() -> CoordinatorRegistry:
    """モジュールレベルのシングルトンを返す。テスト時に差し替え可能。"""
    return _registry


# --- 後方互換の公開API ---

def get_available_generators() -> dict[GeneratorId, GeneratorInfo]:
    return _registry.available_generators


def get_coordinator_id() -> CoordinatorId | None:
    return _registry.coordinator_id


def add_on_generator_registered_callback(callback: Any) -> None:
    _registry.add_on_generator_registered_callback(callback)


def remove_on_generator_registered_callback(callback: Any) -> None:
    _registry.remove_on_generator_registered_callback(callback)


def add_on_generator_removed_callback(callback: Any) -> None:
    _registry.add_on_generator_removed_callback(callback)


def remove_on_generator_removed_callback(callback: Any) -> None:
    _registry.remove_on_generator_removed_callback(callback)


def remove_generator(generator_info: GeneratorInfo) -> None:
    _registry.remove_generator(generator_info)


# --- FastAPI Router ---

router = APIRouter()


@router.post("/comm/register")
async def register_generator(
    request: Request,
    registration_data: GeneratorRegistrationRequest,
) -> GeneratorRegistrationResponse:
    if _registry.coordinator_id is None:
        raise HTTPException(status_code=500, detail="Coordinator ID not initialized")

    if registration_data.coordinator_id is not None:
        if registration_data.coordinator_id != _registry.coordinator_id:
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
    _registry.register_generator(generator_info)

    return GeneratorRegistrationResponse(coordinator_id=_registry.coordinator_id)


@router.get("/comm/healthz")
async def health_check():
    return {"status": "ok", "coordinator_id": _registry.coordinator_id}


@router.post("/comm/shutdown")
async def shutdown_coordinator():
    """Coordinatorをシャットダウンし、すべてのgeneratorも停止する"""
    logger.warning("Coordinator shutdown requested")
    asyncio.create_task(_coordinator_shutdown())
    return {"status": "shutting_down"}


async def _coordinator_shutdown():
    """コーディネーターをシャットダウンする。すべてのgeneratorにもシャットダウンを送信"""
    await shutdown_all_generators()
    from quicklook.utils.graceful_shutdown import graceful_shutdown
    await graceful_shutdown(sigint_delay=0.5, sigkill_delay=3, reason="Coordinator shutdown")


if config.environment == 'test':  # pragma: no branch

    @router.get("/comm/generators")
    async def list_generators():
        return {"generators": get_available_generators()}

    @router.post("/comm/trigger-heartbeat")
    async def trigger_heartbeat(fail_for_test: bool = False):
        await _heartbeat_check(fail_for_test=fail_for_test)
        return {"status": "ok"}


if config.environment in ('test', 'development'):  # pragma: no branch

    @router.post("/comm/kill-generator/{generator_id}")
    async def kill_generator_by_id(generator_id: str):
        """開発・テスト用: 指定したGeneratorを強制停止する"""
        gid = GeneratorId(generator_id)
        if gid not in _registry.available_generators:
            raise HTTPException(status_code=404, detail=f"Generator {generator_id} not found")
        generator_info = _registry.available_generators[gid]
        await kill_generator(generator_info)
        return {"status": "killed", "generator_id": generator_id}

    @router.post("/comm/kill-random-generator")
    async def kill_random_generator():
        """開発・テスト用: ランダムに1台のGeneratorを強制停止する"""
        import random
        if not _registry.available_generators:
            raise HTTPException(status_code=404, detail="No generators available")
        generator_info = random.choice(list(_registry.available_generators.values()))
        await kill_generator(generator_info)
        return {"status": "killed", "generator_id": generator_info.id}


@asynccontextmanager
async def lifespan(app: Any) -> AsyncIterator[None]:
    async with managed_session():
        _registry.coordinator_id = CoordinatorId(f'c-{uuid.uuid4().hex}')
        logger.info(f"Coordinator ID: {_registry.coordinator_id}")
        heartbeat_task = asyncio.create_task(_heartbeat_checker_loop())
        try:
            yield
        finally:
            heartbeat_task.cancel()
            try:
                await heartbeat_task
            except asyncio.CancelledError:
                pass


async def kill_generator(generator_info: GeneratorInfo) -> None:
    timeout = aiohttp.ClientTimeout(total=config.comm_heartbeat_timeout)
    url = f"{generator_info.url}/comm/shutdown"

    try:
        session = get_session()
        async with session.post(url, timeout=timeout) as response:
            response.raise_for_status()
            logger.info(f"Shutdown request sent to generator {generator_info.id}")
    except Exception as e:
        logger.warning(f"Failed to send shutdown request to {generator_info.id}: {e}")

    _registry.remove_generator(generator_info)


async def shutdown_all_generators() -> None:
    """すべてのgeneratorに停止リクエストを送信する"""
    logger.warning("Shutting down all generators")
    generators = list(_registry.available_generators.values())
    tasks = [kill_generator(g) for g in generators]
    await asyncio.gather(*tasks, return_exceptions=True)


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
        session = get_session()
        try:
            async with session.get(url, timeout=timeout) as response:
                response.raise_for_status()
        except Exception as e:
            logger.warning(f"Health check failed for {generator_info.id}: {e}")
            return generator_info

    tasks = [check_generator(generator_info) for generator_info in _registry.available_generators.values()]
    results = await asyncio.gather(*tasks)
    to_remove = [gid for gid in results if gid is not None]

    for generator_info in to_remove:
        _registry.remove_generator(generator_info)
