from fastapi import APIRouter
from pydantic import BaseModel
from quicklook.config import config


router = APIRouter()


class SystemInfo(BaseModel):
    admin_page: bool = config.admin_page


@router.get('/api/system_info', response_model=SystemInfo)
def get_system_info():
    return SystemInfo()
