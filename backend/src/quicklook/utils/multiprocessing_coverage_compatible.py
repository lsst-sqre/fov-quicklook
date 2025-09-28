import multiprocessing
from contextlib import contextmanager


@contextmanager
def Pool(*args, **kwargs):  # pragma: no branch
    pool = multiprocessing.Pool(*args, **kwargs)
    try:
        yield pool
    finally:
        pool.close()
        pool.join()
