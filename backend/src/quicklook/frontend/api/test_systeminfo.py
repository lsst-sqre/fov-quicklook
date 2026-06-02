from types import SimpleNamespace

from quicklook.config import ButlerScopeConfig
from quicklook.frontend.api import systeminfo


def test_get_system_info_excludes_query_only_injected_defaults(monkeypatch):
    visible = [
        ButlerScopeConfig(
            dataset_type='raw',
            display_name='Raw (Embargo)',
            collection='LSSTCam/raw/all',
            repository_name='embargo',
            instrument='LSSTCam',
        ),
        ButlerScopeConfig(
            dataset_type='preliminary_visit_image',
            display_name='Preliminary (Embargo)',
            collection='LSSTCam/runs/nightlyValidation',
            repository_name='embargo',
            instrument='LSSTCam',
        ),
    ]

    monkeypatch.setattr(
        systeminfo,
        'config',
        SimpleNamespace(
            admin_page=False,
            context_menu_templates=[],
            max_object_storage_usage=123,
            system_info_butler_scopes=visible,
            datasets=[],
        ),
    )

    response = systeminfo.get_system_info()

    assert response.butler_scopes == visible
