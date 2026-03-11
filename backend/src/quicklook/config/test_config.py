from quicklook.config import config


def test_difference_image_uses_runs_collection():
    difference_image = next(
        dt
        for dt in config.ccd_data_types
        if dt.repository_name == 'embargo' and dt.data_type == 'difference_image'
    )

    assert difference_image.collections == ['LSSTCam/runs']
    assert difference_image.data_id_dimension == 'visit'
    assert difference_image.partial is True
