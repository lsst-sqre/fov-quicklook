import tempfile
from dataclasses import dataclass
from pathlib import Path

import astropy.io.fits as pyfits
import mineo_fits_decompress
import numpy

from quicklook.config import config


@dataclass
class Hdu:
    data: numpy.ndarray
    header: dict[str, str]


def fast_open_comressed_fits(path: Path):
    buf = mineo_fits_decompress.decompressed_bytes(path, config.fitsio_decompress_parallel)
    if config.fitsio_memory_saving_mode:
        with tempfile.NamedTemporaryFile() as f:
            f.write(buf)
            f.flush()
            return pyfits.open(f.name)
    return pyfits.HDUList.fromstring(buf)
