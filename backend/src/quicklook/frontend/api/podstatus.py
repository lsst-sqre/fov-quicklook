import logging
import asyncio

from fastapi import APIRouter
from pydantic import BaseModel
from typing import Any

from quicklook.config import config
from quicklook.coordinator.api.podstatus import CoordinatorPodStatus
from quicklook.utils.http_request import http_request
from quicklook.utils.podstatus import PodStatus, pod_status

logger = logging.getLogger('uvicorn')

router = APIRouter()


class StatusResponse(BaseModel):
    frontend: PodStatus
    coordinator: PodStatus
    generators: list[PodStatus]


async def fetch_coordinator_status() -> CoordinatorPodStatus:
    data = await http_request('get', f'{config.coordinator_base_url}/pod_status')
    return CoordinatorPodStatus(**data)


@router.get('/api/status', response_model=StatusResponse)
async def get_pod_status() -> StatusResponse:
    coordinator_task = fetch_coordinator_status()
    pod_status_task = pod_status()
    coordinator_response, frontend = await asyncio.gather(
        coordinator_task,
        pod_status_task,
    )
    return StatusResponse(
        frontend=frontend,
        coordinator=coordinator_response.coordinator,
        generators=coordinator_response.generators,
    )
