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
