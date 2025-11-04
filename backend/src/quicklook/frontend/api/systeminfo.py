from fastapi import APIRouter
from pydantic import BaseModel

from quicklook.config import ContextMenuTemplate, config

router = APIRouter()


class SystemInfo(BaseModel):
    admin_page: bool
    context_menu_templates: list[ContextMenuTemplate]
    max_object_storage_usage: int


@router.get('/api/system_info', response_model=SystemInfo)
def get_system_info():
    return SystemInfo(
        admin_page=config.admin_page,
        context_menu_templates=config.context_menu_templates,
        max_object_storage_usage=config.max_object_storage_usage,
    )
