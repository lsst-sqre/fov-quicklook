import tempfile
from contextlib import contextmanager
from pathlib import Path

from quicklook.config import config
from quicklook.generator.preprocess_ccd import preprocess_ccd
from quicklook.types import CcdId, Visit
from quicklook.utils.fits import preload_pyfits_compression_code
from quicklook.utils.s3 import s3_download_object


def test_preprocess_ccd_raw():
    ccd_id = CcdId(Visit('raw:broccoli'), 'R00_SG0')
    with fits_path(ccd_id) as path:
        preprocess_ccd(ccd_id, path)


def test_preprocess_ccd_calexp():
    ccd_id = CcdId(Visit('calexp:192350'), 'R01_S00')
    with fits_path(ccd_id) as path:
        preprocess_ccd(ccd_id, path)


def fits_bytes(ccd_id: CcdId) -> bytes:
    key = f'{ccd_id.visit.data_type}/{ccd_id.visit.name}/{ccd_id.ccd_name}.fits'
    return s3_download_object(config.s3_test_data, key)


@contextmanager
def fits_path(ccd_id: CcdId):
    with tempfile.NamedTemporaryFile() as f:
        Path(f.name).write_bytes(fits_bytes(ccd_id))
        yield Path(f.name)


preload_pyfits_compression_code()
