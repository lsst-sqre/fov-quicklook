import tempfile
from contextlib import contextmanager
from pathlib import Path

import mineo_fits_decompress

from quicklook.config import config
from quicklook.generator.preprocess_ccd import fast_open_comressed_fits, preprocess_ccd
from quicklook.types import CcdDataRef, CcdName, VisitName
from quicklook.utils.fits import preload_pyfits_compression_code
from quicklook.utils.s3 import s3_download_object


def test_preprocess_ccd_raw():
    ccd_ref = CcdDataRef(visit=VisitName('raw:broccoli'), ccd=CcdName('R00_SG0'))
    with fits_path(ccd_ref) as path:
        preprocess_ccd(ccd_ref, path)


def test_preprocess_ccd_calexp():
    ccd_ref = CcdDataRef(visit=VisitName('calexp:192350'), ccd=CcdName('R01_S00'))
    with fits_path(ccd_ref) as path:
        preprocess_ccd(ccd_ref, path)


def fits_bytes(ref: CcdDataRef) -> bytes:
    key = f'{ref.visit.data_type}/{ref.visit.name}/{ref.ccd_name}.fits'
    return s3_download_object(config.s3_test_data, key)


@contextmanager
def fits_path(ref: CcdDataRef):
    with tempfile.NamedTemporaryFile() as f:
        Path(f.name).write_bytes(fits_bytes(ref))
        yield Path(f.name)


preload_pyfits_compression_code()
