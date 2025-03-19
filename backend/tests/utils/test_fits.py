import tempfile

import astropy.io.fits as pyfits
import minio

from quicklook.config import config
from quicklook.types import Visit
from quicklook.utils.fits import fits_partial_load
from quicklook.utils.s3 import s33_download_object


def test_s3_partial_load():
    visit = Visit.from_id('calexp:192350')
    ccd_name = 'R11_S21'

    def read(start: int, end: int) -> bytes:
        key = f'{visit.data_type}/{visit.name}/{ccd_name}.fits'
        return s33_download_object(config.s3_test_data, key, offset=start, length=end - start)

    data = fits_partial_load(read, [0, 1])
    with tempfile.NamedTemporaryFile(suffix='.fits') as f:
        f.write(data)
        f.flush()
        with pyfits.open(f.name) as hdul:  # type: ignore
            hdul[1].data[-1]  # type: ignore
