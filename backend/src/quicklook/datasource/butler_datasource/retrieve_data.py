import logging
from lsst.resources import ResourcePath
from lsst.resources.s3 import S3ResourcePath

from quicklook.utils.fits import fits_partial_load

logger = logging.getLogger(f'uvicorn.{__name__}')


def retrieve_data(uri: ResourcePath, *, partial=False) -> bytes:  # pragma: no cover
    if isinstance(uri, S3ResourcePath):
        if partial:

            def read(start: int, end: int) -> bytes:
                if start != 0:
                    raise ValueError("S3ResourcePath does not support partial read")
                return uri.read(size=end)

            return fits_partial_load(read=read, hdu_index=[0, 1])
        uri = ResourcePath(uri)
    return uri.read()
