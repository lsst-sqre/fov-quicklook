import tempfile

import astropy.io.fits as pyfits
import numpy

from quicklook.config import config
from quicklook.types import VisitName
from quicklook.utils.fits import fits_partial_load
from quicklook.utils.s3 import s3_download_object


def test_s3_partial_load():
    visit = VisitName('dummy:calexp:192350')
    ccd_name = 'R11_S21'

    def read(start: int, end: int) -> bytes:
        key = f'{visit.data_type}/{visit.name}/{ccd_name}.fits'
        return s3_download_object(config.s3_test_data, key, offset=start, length=end - start)

    data = fits_partial_load(read, [0, 1])
    with tempfile.NamedTemporaryFile(suffix='.fits') as f:
        f.write(data)
        f.flush()
        with pyfits.open(f.name) as hdul:  # type: ignore
            hdul[1].data[-1]  # type: ignore


def test_partial_load_supports_later_hdu_indices():
    hdus = [pyfits.PrimaryHDU()]
    hdus.append(pyfits.ImageHDU(data=numpy.zeros((2, 2), dtype=numpy.float32), name="IMAGE"))
    hdus.append(pyfits.ImageHDU(data=numpy.zeros((2, 2), dtype=numpy.float32), name="MASK"))
    hdus.append(pyfits.ImageHDU(data=numpy.zeros((2, 2), dtype=numpy.float32), name="VARIANCE"))
    hdus.append(
        pyfits.BinTableHDU.from_columns([
            pyfits.Column(name="id", format="J", array=[4]),
            pyfits.Column(name="cat.archive", format="J", array=[4]),
            pyfits.Column(name="cat.persistable", format="J", array=[0]),
            pyfits.Column(name="row0", format="J", array=[0]),
            pyfits.Column(name="nrows", format="J", array=[1]),
            pyfits.Column(name="name", format="20A", array=["TransformPoint2ToPoint2"]),
            pyfits.Column(name="module", format="20A", array=["lsst.afw.geom"]),
        ], name="ARCHIVE_INDEX")
    )
    hdus.append(pyfits.BinTableHDU.from_columns([pyfits.Column(name="bytes", format="4B", array=[[1, 2, 3, 4]])], name="FilterLabel"))
    hdus.append(pyfits.BinTableHDU.from_columns([pyfits.Column(name="bytes", format="4B", array=[[1, 2, 3, 4]])], name="Detector"))
    hdus.append(pyfits.BinTableHDU.from_columns([pyfits.Column(name="bytes", format="4B", array=[[1, 2, 3, 4]])], name="TransformMap"))
    hdus.append(pyfits.BinTableHDU.from_columns([pyfits.Column(name="bytes", format="4B", array=[[1, 2, 3, 4]])], name="TransformPoint2ToPoint2"))

    with tempfile.NamedTemporaryFile(suffix=".fits") as f:
        pyfits.HDUList(hdus).writeto(f.name)
        with open(f.name, "rb") as src:
            payload = src.read()

        def read(start: int, end: int) -> bytes:
            return payload[start:end]

        data = fits_partial_load(read, [0, 1, 7, 8])

    with tempfile.NamedTemporaryFile(suffix=".fits") as f:
        f.write(data)
        f.flush()
        with pyfits.open(f.name) as hdul:  # type: ignore
            assert len(hdul) == 9
            assert hdul[8].name == "TRANSFORMPOINT2TOPOINT2"
