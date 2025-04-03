from fastapi import APIRouter

from quicklook.config import config
from quicklook.utils.http_request import http_request

router = APIRouter()


@router.get('/api/healthz')
async def healthz():
    return {'status': 'ok'}


@router.get('/api/ready')
async def ready():
    return await http_request('get', f'{config.coordinator_base_url}/ready')
