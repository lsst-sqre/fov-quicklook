import contextlib
import logging
import time

from quicklook.config import config


class settings:
    logger = logging.getLogger(f'uvicorn.{__name__}')
    loglevel = logging._nameToLevel[config.timeit_log_level]


@contextlib.contextmanager
def timeit(
    label: str,
    *,
    loglevel: int | None = None,
    logger: logging.Logger | None = None,
):
    if loglevel is None:
        loglevel = settings.loglevel
    if logger is None:  # pragma: no branch
        logger = settings.logger
    start = time.time()
    try:
        yield
    finally:
        elapsed = time.time() - start
        settings.logger.log(loglevel, f"{label}: {elapsed:.3f}s")
