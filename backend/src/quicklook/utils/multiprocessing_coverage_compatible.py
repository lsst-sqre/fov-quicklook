import multiprocessing
from contextlib import contextmanager


@contextmanager
def Pool(parallel: int | None = None):  # pragma: no branch
    pool = multiprocessing.Pool(parallel)
    try:
        yield pool
    finally:
        pool.close()
        pool.join()
