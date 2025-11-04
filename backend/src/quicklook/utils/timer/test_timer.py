from __future__ import annotations

import threading
import time
from typing import Iterator

import pytest

from quicklook.utils.timer import Timer, get_check_interval, set_check_interval


@pytest.fixture(autouse=True)
def short_check_interval() -> Iterator[None]:
    previous = get_check_interval()
    set_check_interval(0.01)
    try:
        yield
    finally:
        set_check_interval(previous)


def _set_event(event: threading.Event) -> None:
    event.set()


def _append(target: list[str], value: str) -> None:
    target.append(value)


def test_timer_executes_once() -> None:
    event = threading.Event()
    timer = Timer(0.02, _set_event, args=(event,))
    timer.start()

    assert timer.is_alive()
    assert event.wait(0.5)
    assert timer.wait(0.5)

    assert timer.finished
    assert not timer.is_alive()


def test_timer_cancel_prevents_execution() -> None:
    event = threading.Event()
    timer = Timer(0.05, _set_event, args=(event,))
    timer.start()
    timer.cancel()

    assert timer.finished
    assert not timer.is_alive()
    assert timer.wait(0.01)
    time.sleep(0.1)
    assert not event.is_set()


def test_multiple_timers_run_in_order() -> None:
    results: list[str] = []

    timer_fast = Timer(0.01, _append, args=(results, "fast"))
    timer_slow = Timer(0.04, _append, args=(results, "slow"))

    timer_fast.start()
    timer_slow.start()

    deadline = time.monotonic() + 0.5
    while len(results) < 2 and time.monotonic() < deadline:
        time.sleep(0.005)

    assert results == ["fast", "slow"]
    assert timer_fast.finished
    assert timer_slow.finished
