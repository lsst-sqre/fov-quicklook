from fastapi import APIRouter
from pydantic import BaseModel

from quicklook.config import ButlerScopeConfig, ContextMenuTemplate, config

router = APIRouter()


class SystemInfo(BaseModel):
    admin_page: bool
    context_menu_templates: list[ContextMenuTemplate]
    max_object_storage_usage: int
    butler_scopes: list[ButlerScopeConfig]
    datasets: list[dict[str, object]]


@router.get('/api/system_info', response_model=SystemInfo)
def get_system_info():
    return SystemInfo(
        admin_page=config.admin_page,
        context_menu_templates=config.context_menu_templates,
        max_object_storage_usage=config.max_object_storage_usage,
        butler_scopes=config.system_info_butler_scopes,
        datasets=config.datasets,
    )
