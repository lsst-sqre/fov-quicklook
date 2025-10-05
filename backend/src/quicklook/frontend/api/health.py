from fastapi import APIRouter

from quicklook.config import config
from quicklook.utils.http_request import http_request

router = APIRouter()


@router.get('/api/healthz')
async def healthz():
    return {'status': 'ok'}
