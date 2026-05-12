from fastapi import APIRouter
from pydantic import BaseModel

from quicklook.config import CcdDataTypeConfig, ContextMenuTemplate, config

router = APIRouter()


class SystemInfo(BaseModel):
    admin_page: bool
    context_menu_templates: list[ContextMenuTemplate]
    max_object_storage_usage: int
    ccd_data_types: list[CcdDataTypeConfig]


@router.get('/api/system_info', response_model=SystemInfo)
def get_system_info():
    return SystemInfo(
        admin_page=config.admin_page,
        context_menu_templates=config.context_menu_templates,
        max_object_storage_usage=config.max_object_storage_usage,
        ccd_data_types=config.system_info_ccd_data_types,
    )
