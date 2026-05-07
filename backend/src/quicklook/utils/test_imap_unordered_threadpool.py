import threading
import time
from concurrent.futures import ThreadPoolExecutor

from quicklook.utils.imap_unordered_threadpool import imap_unordered_threadpool


class _BlockingIterator:
    def __init__(self, release_event: threading.Event) -> None:
        self._values = iter((1, 2))
        self._release_event = release_event
        self._waited = False

    def __iter__(self):
        return self

    def __next__(self) -> int:
        try:
            return next(self._values)
        except StopIteration:
            if not self._waited:
                self._waited = True
                self._release_event.wait(timeout=5)
            raise


def test_imap_unordered_threadpool_yields_completed_work_before_input_exhausts():
    release_event = threading.Event()
    timer = threading.Timer(0.5, release_event.set)
    timer.start()

    try:
        with ThreadPoolExecutor(max_workers=2) as executor:
            results = imap_unordered_threadpool(
                executor,
                lambda value: value,
                _BlockingIterator(release_event),
                max_in_flight=4,
            )

            start = time.monotonic()
            first = next(results)
            elapsed = time.monotonic() - start

            assert elapsed < 0.3
            assert first in {1, 2}
            assert sorted([first, *results]) == [1, 2]
    finally:
        release_event.set()
        timer.cancel()
