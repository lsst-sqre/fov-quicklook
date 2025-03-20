from contextlib import contextmanager
import threading


@contextmanager
def run_thread(t: threading.Thread):
    t.start()
    try:
        yield
    finally:
        t.join()
