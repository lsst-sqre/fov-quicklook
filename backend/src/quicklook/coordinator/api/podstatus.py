from dataclasses import dataclass
from fastapi import APIRouter
from pydantic import BaseModel
import asyncio

from quicklook.coordinator.api.generators import ctx
from quicklook.utils.http_request import http_request
from quicklook.utils.podstatus import PodStatus, pod_status

router = APIRouter()


class CoordinatorPodStatus(BaseModel):
    coordinator: PodStatus
    generators: list[PodStatus]


@router.get('/pod_status')
async def get_pod_status() -> CoordinatorPodStatus:
    return CoordinatorPodStatus(
        coordinator=await pod_status(storage_dirs=[]),
        generators=await asyncio.gather(
            *[
                http_request(
                    'GET',
                    f'http://{g.host}:{g.port}/pod_status',
                )
                for g in ctx().generators
            ]
        ),
    )
