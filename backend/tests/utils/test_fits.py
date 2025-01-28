import tempfile

import astropy.io.fits as pyfits
import minio

from quicklook.config import config
from quicklook.types import Visit
from quicklook.utils.fits import fits_partial_load
from quicklook.utils.s3 import download_object_from_s3


def test_s3_partial_load():
    visit = Visit('calexp', '192350')
    ccd_name = 'R11_S21'

    def read(start: int, end: int) -> bytes:
        bucket = config.s3_repository.bucket
        key = f'{visit.data_type}/{visit.name}/{ccd_name}.fits'
        return download_object_from_s3(s3_client(), bucket, key, offset=start, length=end - start)

    data = fits_partial_load(read, [0, 1])
    with tempfile.NamedTemporaryFile(suffix='.fits') as f:
        f.write(data)
        f.flush()
        with pyfits.open(f.name) as hdul:
            hdul[1].data[-1]  # type: ignore


def s3_client():
    s3_config = config.s3_repository
    return minio.Minio(
        s3_config.endpoint,
        access_key=s3_config.access_key,
        secret_key=s3_config.secret_key,
        secure=s3_config.secure,
    )
