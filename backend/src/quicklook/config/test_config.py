from quicklook.config import Config, config


def test_difference_image_uses_visit_dimension():
    difference_image = next(
        dt
        for dt in config.ccd_data_types
        if dt.repository_name == 'embargo' and dt.data_type == 'difference_image'
    )

    assert difference_image.data_id_dimension == 'visit'
    assert difference_image.partial is True


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


def test_config_adds_missing_default_ccd_data_types_from_env_file(tmp_path, monkeypatch):
    env_file = tmp_path / "stale-review-app.env"
    env_file.write_text(
        "\n".join(
            [
                'QUICKLOOK_ccd_data_types=[{"data_type":"raw","display_name":"Raw (Embargo)","collections":["LSSTCam/raw/all"],"data_id_dimension":"exposure","order_by":["-day_obs","-exposure"],"partial":false,"repository_name":"embargo","instrument":"LSSTCam"},{"data_type":"post_isr_image","display_name":"Post-ISR (Embargo)","collections":["LSSTCam/runs/nightlyValidation"],"data_id_dimension":"exposure","order_by":["-exposure"],"partial":true,"repository_name":"embargo","instrument":"LSSTCam"},{"data_type":"preliminary_visit_image","display_name":"Preliminary (Embargo)","collections":["LSSTCam/runs/nightlyValidation"],"data_id_dimension":"visit","order_by":["-visit"],"partial":true,"repository_name":"embargo","instrument":"LSSTCam"}]',
                "",
            ]
        )
    )

    monkeypatch.delenv("QUICKLOOK_ccd_data_types", raising=False)
    loaded = Config(_env_file=env_file)

    difference_image = next(
        dt
        for dt in loaded.ccd_data_types
        if dt.repository_name == 'embargo' and dt.data_type == 'difference_image'
    )

    assert difference_image.data_id_dimension == 'visit'
    assert difference_image.partial is True
