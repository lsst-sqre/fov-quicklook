"""
Admin API endpoints.

These endpoints are only available when config.admin_page is True.
"""

import aiohttp
from fastapi import APIRouter
from pydantic import BaseModel

import quicklook.mylogging
from quicklook.config import config

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
    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{config.coordinator_base_url}/comm/shutdown",
            timeout=timeout,
        ) as response:
            response.raise_for_status()
            return ShutdownResponse(status="shutting_down")
