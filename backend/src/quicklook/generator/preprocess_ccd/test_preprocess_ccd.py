import tempfile
from contextlib import contextmanager
from pathlib import Path

from quicklook.config import config
from quicklook.generator.preprocess_ccd import preprocess_ccd
from quicklook.review_app.shared_fixtures import FixtureVisit, generate_raw_fits_bytes
from quicklook.types import CcdDataRef, CcdName, VisitName
from quicklook.utils.fits import preload_pyfits_compression_code
from quicklook.utils.s3 import s3_download_object


def test_preprocess_ccd_raw():
    ccd_ref = CcdDataRef(visit=VisitName('reviewapp-ci:raw:910003'), ccd=CcdName('R01_S00'))
    visit = FixtureVisit(
        exposure_id=910003,
        day_obs=20260503,
        physical_filter='z',
        exposure_time=25.0,
        target_name='fixture-target-3',
        science_program='review-app-fixtures',
    )
    with tempfile.NamedTemporaryFile() as f:
        path = Path(f.name)
        path.write_bytes(generate_raw_fits_bytes(ccd_ref.ccd, seed=910003, visit=visit))
        result = preprocess_ccd(ccd_ref, path)
    assert result.amps
    assert result.stat.mad is not None
    assert result.stat.mad > 0
    assert int((result.pool[:, :, 1] > 0).sum()) > 0


def test_preprocess_ccd_calexp():
    ccd_ref = CcdDataRef(visit=VisitName('dummy:calexp:192350'), ccd=CcdName('R01_S00'))
    with fits_path(ccd_ref) as path:
        preprocess_ccd(ccd_ref, path)


def test_preprocess_ccd_difference_image_uses_calexp_path(monkeypatch):
    expected = object()
    ccd_ref = CcdDataRef(visit=VisitName('dummy:difference_image:192350'), ccd=CcdName('R01_S00'))

    monkeypatch.setattr(
        'quicklook.generator.preprocess_ccd.preprocess_ccd_calexp',
        lambda arg_ref, arg_path: expected,
    )

    assert preprocess_ccd(ccd_ref, Path('difference_image.fits')) is expected


def fits_bytes(ref: CcdDataRef) -> bytes:
    key = f'{ref.visit.data_type}/{ref.visit.name}/{ref.ccd}.fits'
    return s3_download_object(config.s3_test_data, key)


@contextmanager
def fits_path(ref: CcdDataRef):
    with tempfile.NamedTemporaryFile() as f:
        Path(f.name).write_bytes(fits_bytes(ref))
        yield Path(f.name)


preload_pyfits_compression_code()
