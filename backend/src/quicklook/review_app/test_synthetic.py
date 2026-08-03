import tempfile
from pathlib import Path

import numpy

from quicklook.generator.preprocess_ccd import preprocess_ccd
from quicklook.review_app.synthetic import (
    _rotate_channel_180,
    _resample_channel_region,
    render_virtual_raw_fits_bytes,
    render_virtual_science_pixels,
)
from quicklook.types import CcdDataRef, CcdName, VisitName


def test_render_virtual_raw_fits_bytes_preprocesses_to_nonzero_signal():
    ccd_name = CcdName("R22_S11")
    data = render_virtual_raw_fits_bytes(
        ccd_name=ccd_name,
        exposure_id=910001,
        day_obs=20260501,
        physical_filter="r",
        obs_id="fixture-910001",
    )

    with tempfile.NamedTemporaryFile() as f:
        path = Path(f.name)
        path.write_bytes(data)
        result = preprocess_ccd(CcdDataRef(VisitName("reviewapp-ci:raw:910001"), ccd_name), path)

    assert result.amps
    assert result.stat.mad is not None
    assert result.stat.mad > 0
    assert float(result.pool[:, :, 0].max()) > 0
    assert float(result.pool[:, :, 0].min()) < 0


def test_render_virtual_science_pixels_varies_by_filter():
    ccd_name = CcdName("R22_S11")

    r_pixels = render_virtual_science_pixels(ccd_name=ccd_name, exposure_id=910001, physical_filter="r")
    g_pixels = render_virtual_science_pixels(ccd_name=ccd_name, exposure_id=910001, physical_filter="g")

    assert r_pixels.shape == g_pixels.shape
    assert float(numpy.mean(numpy.abs(r_pixels - g_pixels))) > 1.0


def test_resample_channel_region_uses_linear_interpolation():
    channel = numpy.array([[0.0, 10.0], [20.0, 30.0]], dtype=numpy.float32)

    sampled = _resample_channel_region(channel, x0=0.0, x1=1.0, y0=0.0, y1=1.0, width=3, height=3)

    assert sampled.shape == (3, 3)
    assert float(sampled[1, 1]) == 15.0
    assert float(sampled[0, 1]) == 5.0
    assert float(sampled[2, 1]) == 25.0


def test_rotate_channel_180_flips_both_axes():
    channel = numpy.array([[1.0, 2.0], [3.0, 4.0]], dtype=numpy.float32)

    rotated = _rotate_channel_180(channel)

    assert rotated.tolist() == [[4.0, 3.0], [2.0, 1.0]]
