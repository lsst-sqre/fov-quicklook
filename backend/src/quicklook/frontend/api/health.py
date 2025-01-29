from fastapi import APIRouter

from quicklook.config import config
from quicklook.utils.http_request import http_request

router = APIRouter()


@router.get('/api/healthz', description='Health check')
async def healthz():
    return await http_request('get', f'{config.coordinator_base_url}/healthz')
