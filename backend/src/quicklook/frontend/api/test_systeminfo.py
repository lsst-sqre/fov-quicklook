from types import SimpleNamespace

from quicklook.config import CcdDataTypeConfig
from quicklook.frontend.api import systeminfo


def test_get_system_info_excludes_query_only_injected_defaults(monkeypatch):
    visible = [
        CcdDataTypeConfig(
            data_type='raw',
            display_name='Raw (Embargo)',
            collections=['LSSTCam/raw/all'],
            repository_name='embargo',
            instrument='LSSTCam',
        ),
        CcdDataTypeConfig(
            data_type='preliminary_visit_image',
            display_name='Preliminary (Embargo)',
            collections=['LSSTCam/runs/nightlyValidation'],
            data_id_dimension='visit',
            order_by=['-visit'],
            partial=True,
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
            system_info_ccd_data_types=visible,
        ),
    )

    response = systeminfo.get_system_info()

    assert response.ccd_data_types == visible
