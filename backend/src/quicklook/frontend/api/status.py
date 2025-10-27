"""Status endpoint for frontend."""

from fastapi import APIRouter
from pydantic import BaseModel
import re

from quicklook.config import config
from quicklook.utils.system_status import ContainerStatus, get_container_status
from quicklook.utils.http_request import http_request

router = APIRouter()


class SystemStatus(BaseModel):
    """System status including frontend, coordinator, and generators."""

    frontend: ContainerStatus
    coordinator: ContainerStatus
    generators: dict[str, ContainerStatus]


@router.get("/api/status", response_model=SystemStatus)
async def route_get_status() -> SystemStatus:
    """Get system status including frontend, coordinator, and generators."""
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
        # Return default status with zeros on error
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
