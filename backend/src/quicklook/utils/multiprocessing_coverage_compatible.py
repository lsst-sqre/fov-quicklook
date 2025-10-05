import multiprocessing
from contextlib import contextmanager


@contextmanager
def Pool(*args, **kwargs):
    pool = multiprocessing.get_context('spawn').Pool(*args, **kwargs)
    try:
        yield pool
    finally:
        pool.close()
        pool.join()
