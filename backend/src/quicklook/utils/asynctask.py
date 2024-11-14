import asyncio
from contextlib import contextmanager


@contextmanager
def cancel_at_exit(task: asyncio.Task):
    try:
        yield
    finally:
        task.cancel()
