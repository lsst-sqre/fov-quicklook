from __future__ import annotations

import io
from pathlib import Path
from typing import Any, cast

import astropy.io.fits as pyfits
import numpy
import pytest

import mineo_fits_decompress

from .fast_open_comressed_fits import FastHdu, fast_open_comressed_fits
from quicklook.utils.fitsheader import fitsheader_to_list


@pytest.fixture
def sample_fits_bytes() -> bytes:
    primary = pyfits.PrimaryHDU()
    image_data = (numpy.arange(16, dtype=numpy.int16).reshape(4, 4) + 1).astype(numpy.int16)
    image_hdu = pyfits.ImageHDU(data=image_data, name='Segment00')
    image_hdu.header['BSCALE'] = 2
    image_hdu.header['BZERO'] = 10
    hdul = pyfits.HDUList([primary, image_hdu])
    buffer = io.BytesIO()
    hdul.writeto(buffer)
    return buffer.getvalue()


def patch_decompress(monkeypatch: pytest.MonkeyPatch, sample_fits_bytes: bytes) -> None:
    def _decompress(_: Path, __: int) -> bytes:
        return sample_fits_bytes

    monkeypatch.setattr(mineo_fits_decompress, 'decompressed_bytes', _decompress)


def test_fast_open_structure(monkeypatch: pytest.MonkeyPatch, sample_fits_bytes: bytes) -> None:
    patch_decompress(monkeypatch, sample_fits_bytes)
    hdul = fast_open_comressed_fits(Path('dummy.fits'))
    assert len(hdul) == 2
    primary = cast(FastHdu, hdul[0])
    segment = cast(FastHdu, hdul[1])
    assert primary.name == 'PRIMARY'
    assert segment.name.upper() == 'SEGMENT00'
    assert segment.data is not None
    assert segment.data.shape == (4, 4)
    assert segment.header['EXTNAME'] == 'SEGMENT00'


def test_fast_open_data_scaling(monkeypatch: pytest.MonkeyPatch, sample_fits_bytes: bytes) -> None:
    patch_decompress(monkeypatch, sample_fits_bytes)
    hdul = fast_open_comressed_fits(Path('dummy.fits'))
    segment = cast(FastHdu, hdul[1])
    astropy_hdul = pyfits.open(io.BytesIO(sample_fits_bytes))
    try:
        assert segment.data is not None
        ref_hdu = cast(Any, astropy_hdul[1])
        assert ref_hdu.data is not None
        ref_data = cast(numpy.ndarray, ref_hdu.data)
        numpy.testing.assert_allclose(segment.data, ref_data)
    finally:
        astropy_hdul.close()


def test_fitsheader_to_list_compatibility(monkeypatch: pytest.MonkeyPatch, sample_fits_bytes: bytes) -> None:
    patch_decompress(monkeypatch, sample_fits_bytes)
    hdul = fast_open_comressed_fits(Path('dummy.fits'))
    fast_headers = fitsheader_to_list(hdul)
    astropy_hdul = pyfits.open(io.BytesIO(sample_fits_bytes))
    try:
        reference_headers = fitsheader_to_list(astropy_hdul)
    finally:
        astropy_hdul.close()
    assert fast_headers == reference_headers


def test_lazy_materialization(monkeypatch: pytest.MonkeyPatch, sample_fits_bytes: bytes) -> None:
    patch_decompress(monkeypatch, sample_fits_bytes)
    hdul = fast_open_comressed_fits(Path('dummy.fits'))
    segment = cast(FastHdu, hdul[1])
    assert getattr(segment, '_data') is None  # type: ignore[attr-defined]
    assert getattr(segment, '_header') is None  # type: ignore[attr-defined]
    _ = segment.data
    _ = segment.header
    assert getattr(segment, '_data') is not None  # type: ignore[attr-defined]
    assert getattr(segment, '_header') is not None  # type: ignore[attr-defined]
