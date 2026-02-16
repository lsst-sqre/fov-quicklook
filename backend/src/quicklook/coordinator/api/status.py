"""Status endpoint for coordinator."""

from fastapi import APIRouter
from pydantic import BaseModel
import aiohttp

from quicklook.comm.types import GeneratorId
from quicklook.config import config
from quicklook.utils.system_status import ContainerStatus, get_container_status
from quicklook.comm.coordinator import get_available_generators
from quicklook.utils.http_client import get_session

router = APIRouter()


class CoordinatorStatus(BaseModel):
    """Status of coordinator and its generators."""

    coordinator: ContainerStatus
    generators: dict[GeneratorId, ContainerStatus]


@router.get("/status", response_model=CoordinatorStatus)
async def route_get_status() -> CoordinatorStatus:
    """Get coordinator and generators status."""
    coordinator_status = get_container_status()

    generators_status: dict[GeneratorId, ContainerStatus] = {}
    available_generators = get_available_generators()

    # Fetch status from all generators in parallel
    timeout = aiohttp.ClientTimeout(total=config.comm_heartbeat_timeout)

    async def fetch_generator_status(
        generator_id: GeneratorId,
        generator_info,
    ) -> tuple[GeneratorId, ContainerStatus]:
        url = f"{generator_info.url}/status"
        try:
            session = get_session()
            async with session.get(url, timeout=timeout) as response:
                response.raise_for_status()
                data = await response.json()
                return generator_id, ContainerStatus(**data)
        except Exception:
            # Return default status with zeros on error
            return generator_id, ContainerStatus(
                container_name=f"generator-{generator_id}",
                memory_max=0,
                memory_current=0,
                cpu_max=0,
                cpu_current=0,
                uptime=0.0,
                memory_stats=None,
            )

    if available_generators:
        import asyncio

        tasks = [fetch_generator_status(gen_id, gen_info) for gen_id, gen_info in available_generators.items()]
        results = await asyncio.gather(*tasks)
        generators_status = dict(results)

    return CoordinatorStatus(
        coordinator=coordinator_status,
        generators=generators_status,
    )
