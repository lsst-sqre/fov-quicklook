import tempfile
import io
import pickle
from pathlib import Path

import minio

from quicklook.config import config
from quicklook.generator.preprocess_ccd import preprocess_ccd
from quicklook.types import CcdId, Visit
from quicklook.utils.fits import preload_pyfits_compression_code
from quicklook.utils.s3 import download_object_from_s3
from quicklook.utils.timeit import timeit


def test_preprocess_ccd_raw():
    visit = Visit.from_id('raw:20230511PH')
    with timeit('load-fits'):
        file_contents = download_object_from_s3(config.s3_test_data, f'raw/broccoli/R00_SG0.fits')

        with timeit('preprocess'):
            with tempfile.NamedTemporaryFile() as f:
                Path(f.name).write_bytes(file_contents)
                ppccd = preprocess_ccd(CcdId(visit, 'R00_SG0'), Path(f.name))


def test_preprocess_ccd_calexp():
    visit = Visit.from_id('calexp:192350')
    with timeit('load-fits'):
        file_contents = download_object_from_s3(config.s3_test_data, f'calexp/192350/R01_S00.fits')

        with timeit('preprocess'):
            with tempfile.NamedTemporaryFile() as f:
                Path(f.name).write_bytes(file_contents)
                ppccd = preprocess_ccd(CcdId(visit, 'R01_S00'), Path(f.name))


preload_pyfits_compression_code()
