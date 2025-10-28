"""Status endpoint for frontend."""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
import re
import asyncio
import json

from quicklook.config import config
from quicklook.utils.system_status import ContainerStatus, get_container_status
from quicklook.utils.http_request import http_request
from quicklook.utils.ttlcache import ttlcache

router = APIRouter()


class SystemStatus(BaseModel):
    """System status including frontend, coordinator, and generators."""

    frontend: ContainerStatus
    coordinator: ContainerStatus
    generators: dict[str, ContainerStatus]


@ttlcache(ttl=1.0)
async def get_cached_status() -> SystemStatus:
    """Get system status with 1-second cache."""
    frontend_status = get_container_status()

    try:
        coordinator_data = await http_request(
            "get",
            f"{config.coordinator_base_url}/status",
        )
        coordinator_status = ContainerStatus(**coordinator_data["coordinator"])
        generators_status = {
            gen_id: ContainerStatus(**gen_data)
            for gen_id, gen_data in coordinator_data["generators"].items()
        }
    except Exception:
        coordinator_status = ContainerStatus(
            container_name="coordinator",
            memory_max=0,
            memory_current=0,
            cpu_max=0,
            cpu_current=0,
            uptime=0.0,
            memory_stats=None,
        )
        generators_status = {}

    return SystemStatus(
        frontend=frontend_status,
        coordinator=coordinator_status,
        generators=generators_status,
    )


@router.get("/api/status", response_model=SystemStatus)
async def route_get_status() -> SystemStatus:
    """Get system status including frontend, coordinator, and generators."""
    return await get_cached_status()


@router.websocket("/api/status/ws")
async def status_websocket(websocket: WebSocket) -> None:
    """WebSocket endpoint for real-time system status updates."""
    await websocket.accept()
    try:
        while True:
            status = await get_cached_status()
            await websocket.send_text(status.model_dump_json())
            await asyncio.sleep(1.0)
    except WebSocketDisconnect:
        pass
    except Exception:
        await websocket.close()
