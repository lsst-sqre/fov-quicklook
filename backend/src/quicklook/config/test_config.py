from quicklook.config import Config, config
from quicklook.datasets import get_dataset


def test_difference_image_uses_visit_dimension():
    difference_image = get_dataset('difference_image')

    assert difference_image.quicklook_dimension == 'visit'
    assert difference_image.partial is True


def test_generate_single_fits_tiles_timeout_default_is_300_seconds(monkeypatch):
    monkeypatch.delenv("QUICKLOOK_generate_single_fits_tiles_timeout_seconds", raising=False)

    loaded = Config()

    assert loaded.generate_single_fits_tiles_timeout_seconds == 300.0


def test_config_ignores_non_quicklook_entries_in_env_file(tmp_path, monkeypatch):
    env_file = tmp_path / "review-app.env"
    env_file.write_text(
        "\n".join(
            [
                "DAF_BUTLER_REPOSITORY_INDEX=/tmp/data-repos.yaml",
                "QUICKLOOK_data_source=butler",
                "",
            ]
        )
    )

    monkeypatch.delenv("QUICKLOOK_data_source", raising=False)
    loaded = Config(_env_file=env_file)

    assert loaded.data_source == "butler"


def test_config_adds_missing_default_butler_scopes_from_env_file(tmp_path, monkeypatch):
    env_file = tmp_path / "stale-review-app.env"
    env_file.write_text(
        "\n".join(
            [
                'QUICKLOOK_ccd_data_types=[{"data_type":"raw","display_name":"Raw (Embargo)","collections":["LSSTCam/raw/all"],"repository_name":"embargo","instrument":"LSSTCam"},{"data_type":"post_isr_image","display_name":"Post-ISR (Embargo)","collections":["LSSTCam/runs/nightlyValidation"],"repository_name":"embargo","instrument":"LSSTCam"},{"data_type":"preliminary_visit_image","display_name":"Preliminary (Embargo)","collections":["LSSTCam/runs/nightlyValidation"],"repository_name":"embargo","instrument":"LSSTCam"}]',
                "",
            ]
        )
    )

    monkeypatch.delenv("QUICKLOOK_ccd_data_types", raising=False)
    loaded = Config(_env_file=env_file)

    difference_image = next(
        scope
        for scope in loaded.butler_scopes
        if scope.repository_name == 'embargo' and scope.dataset_type == 'difference_image'
    )

    assert difference_image.collection == 'LSSTCam/runs/nightlyValidation'


def test_system_info_butler_scopes_excludes_injected_defaults_from_env_file(tmp_path, monkeypatch):
    env_file = tmp_path / "stale-review-app.env"
    env_file.write_text(
        "\n".join(
            [
                'QUICKLOOK_ccd_data_types=[{"data_type":"raw","display_name":"Raw (Embargo)","collections":["LSSTCam/raw/all"],"repository_name":"embargo","instrument":"LSSTCam"},{"data_type":"post_isr_image","display_name":"Post-ISR (Embargo)","collections":["LSSTCam/runs/nightlyValidation"],"repository_name":"embargo","instrument":"LSSTCam"},{"data_type":"preliminary_visit_image","display_name":"Preliminary (Embargo)","collections":["LSSTCam/runs/nightlyValidation"],"repository_name":"embargo","instrument":"LSSTCam"}]',
                "",
            ]
        )
    )

    monkeypatch.delenv("QUICKLOOK_ccd_data_types", raising=False)
    loaded = Config(_env_file=env_file)

    assert [(scope.repository_name, scope.dataset_type) for scope in loaded.system_info_butler_scopes] == [
        ("embargo", "raw"),
        ("embargo", "post_isr_image"),
        ("embargo", "preliminary_visit_image"),
    ]


def test_config_does_not_inject_default_repositories_into_custom_fixture_env(tmp_path, monkeypatch):
    env_file = tmp_path / "review-app.env"
    env_file.write_text(
        "\n".join(
            [
                'QUICKLOOK_ccd_data_types=[{"data_type":"raw","display_name":"Raw (CI fixture)","collections":["LSSTCam/raw/all"],"repository_name":"reviewapp-ci","instrument":"LSSTCam"}]',
                "",
            ]
        )
    )

    monkeypatch.delenv("QUICKLOOK_ccd_data_types", raising=False)
    loaded = Config(_env_file=env_file)

    assert [(scope.repository_name, scope.dataset_type) for scope in loaded.butler_scopes] == [
        ("reviewapp-ci", "raw")
    ]
