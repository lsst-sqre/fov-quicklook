"""
Admin API endpoints.

These endpoints are only available when config.admin_page is True.
"""

import aiohttp
from fastapi import APIRouter
from pydantic import BaseModel

import quicklook.mylogging
from quicklook.config import config
from quicklook.utils.http_client import get_session

logger = quicklook.mylogging.getLogger(__name__)

router = APIRouter(prefix="/api/admin", tags=["admin"])


class ShutdownResponse(BaseModel):
    status: str


@router.post("/kill_coordinator")
async def kill_coordinator() -> ShutdownResponse:
    """
    Coordinator をシャットダウンし、全 Generator も停止させる。
    k8s が自動的に再起動するため、システム全体が再起動される。
    """
    logger.warning("Admin requested coordinator shutdown")
    
    timeout = aiohttp.ClientTimeout(total=10)
    session = get_session()
    async with session.post(
        f"{config.coordinator_base_url}/comm/shutdown",
        timeout=timeout,
    ) as response:
        response.raise_for_status()
        return ShutdownResponse(status="shutting_down")


class KillGeneratorResponse(BaseModel):
    status: str
    generator_id: str


@router.post("/kill_random_generator")
async def kill_random_generator() -> KillGeneratorResponse:
    """
    ランダムに1台の Generator を強制停止する。
    development/test 環境のみ有効（coordinator 側で制御）。
    """
    logger.warning("Admin requested random generator kill")

    timeout = aiohttp.ClientTimeout(total=10)
    session = get_session()
    async with session.post(
        f"{config.coordinator_base_url}/comm/kill-random-generator",
        timeout=timeout,
    ) as response:
        response.raise_for_status()
        data = await response.json()
        return KillGeneratorResponse(**data)
