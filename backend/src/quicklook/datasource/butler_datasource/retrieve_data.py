import logging
import os

from lsst.resources import ResourcePath
from lsst.resources.file import FileResourcePath
from lsst.resources.s3 import S3ResourcePath
from quicklook.utils.fits import fits_partial_load

logger = logging.getLogger(__name__)


def _log_memory(label: str) -> None:
    """RSS(Resident Set Size)をMB単位でログ出力する"""
    try:
        import resource
        rss_kb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        rss_mb = rss_kb / 1024
        logger.info("Memory[%s]: RSS=%.1fMB, PID=%d", label, rss_mb, os.getpid())
    except Exception:
        pass


def retrieve_data(uri: ResourcePath, *, partial=False) -> bytes:  # pragma: no cover
    logger.info("retrieve_data: uri=%s, type=%s, partial=%s", uri, type(uri).__name__, partial)
    _log_memory("before_read")

    if partial:

        def read(start: int, end: int) -> bytes:
            if start != 0:
                raise ValueError("Non -zero start not supported")
            return uri.read(size=end)

        match uri:
            case S3ResourcePath():
                data = fits_partial_load(read=read, hdu_index=[0, 1])
                logger.info("retrieve_data: partial read %d bytes from S3", len(data))
                _log_memory("after_partial_read")
                return data
            case FileResourcePath():
                data = fits_partial_load(read=read, hdu_index=[0, 1])
                logger.info("retrieve_data: partial read %d bytes from file", len(data))
                _log_memory("after_partial_read")
                return data

    data = uri.read()
    logger.info("retrieve_data: full read %d bytes", len(data))
    _log_memory("after_full_read")
    return data
