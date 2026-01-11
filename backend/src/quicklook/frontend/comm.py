"""
Frontend API側の通信モジュール。

Coordinatorとの疎通を定期的に確認し、Coordinator IDが変化した場合は
自プロセスを終了する（k8sによる再起動でCoordinatorに追従）。
"""

import asyncio
import os
import signal
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

import aiohttp

import quicklook.mylogging
from quicklook.comm.types import CoordinatorId
from quicklook.config import config

logger = quicklook.mylogging.getLogger(__name__)


_coordinator_id: CoordinatorId | None = None


def get_coordinator_id() -> CoordinatorId | None:
    """Frontend APIが認識しているCoordinator IDを返す"""
    return _coordinator_id


@asynccontextmanager
async def lifespan(app: Any) -> AsyncIterator[None]:
    """
    Frontend API起動時にCoordinator IDを取得し、定期的に確認するタスクを開始。
    """
    check_task = asyncio.create_task(_coordinator_check_loop())
    try:
        yield
    finally:
        check_task.cancel()
        try:
            await check_task
        except asyncio.CancelledError:
            pass


async def _coordinator_check_loop():
    """定期的にCoordinator IDを確認し、変化したら再起動"""
    global _coordinator_id

    while True:
        await asyncio.sleep(config.comm_registration_interval)
        try:
            current_id = await _fetch_coordinator_id()
            if current_id is None:
                continue

            if _coordinator_id is None:
                _coordinator_id = current_id
                logger.info(f"Frontend: Received coordinator ID: {_coordinator_id}")
            elif _coordinator_id != current_id:
                logger.error(
                    f"Frontend: Coordinator ID changed from {_coordinator_id} to {current_id}. "
                    "Coordinator has been restarted."
                )
                await _shutdown()
        except Exception as e:
            logger.warning(f"Frontend: Error checking coordinator: {e}")


async def _fetch_coordinator_id() -> CoordinatorId | None:
    """CoordinatorのhealthzエンドポイントからCoordinator IDを取得"""
    timeout = aiohttp.ClientTimeout(total=config.comm_heartbeat_timeout)
    url = f"{config.coordinator_base_url}/comm/healthz"

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=timeout) as response:
                response.raise_for_status()
                data = await response.json()
                coordinator_id = data.get("coordinator_id")
                if coordinator_id:
                    return CoordinatorId(coordinator_id)
                return None
    except Exception as e:
        logger.debug(f"Frontend: Failed to fetch coordinator ID: {e}")
        return None


async def _shutdown():
    """Frontend APIプロセスを終了"""
    logger.warning("Frontend: Shutting down due to coordinator restart")
    await asyncio.sleep(1)
    os.kill(os.getpid(), signal.SIGINT)
    await asyncio.sleep(5)
    os.kill(os.getpid(), signal.SIGKILL)  # pragma: no cover
