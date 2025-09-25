from __future__ import annotations

import heapq
import itertools
import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable

__all__ = ["Timer", "set_check_interval", "get_check_interval"]

logger = logging.getLogger(__name__)

_DEFAULT_CHECK_INTERVAL = 1.0


def set_check_interval(interval: float) -> None:
    """Update the polling interval of the timer manager."""
    if interval <= 0:
        msg = "interval must be greater than zero"
        raise ValueError(msg)
    _get_manager().set_check_interval(interval)


def get_check_interval() -> float:
    """Return the current polling interval of the timer manager."""
    return _get_manager().get_check_interval()


class Timer:
    """A single-shot timer similar to :class:`threading.Timer`."""

    def __init__(
        self,
        interval: float,
        function: Callable[..., Any],
        args: tuple[Any, ...] | None = None,
        kwargs: dict[str, Any] | None = None,
    ) -> None:
        if interval < 0:
            msg = "interval must be non-negative"
            raise ValueError(msg)
        if not callable(function):
            msg = "function must be callable"
            raise TypeError(msg)

        self.function = function
        self.args = args if args is not None else ()
        self.kwargs = kwargs if kwargs is not None else {}

        self._interval = float(interval)
        self._started = False
        self._cancelled = False
        self._fired = False
        self._lock = threading.Lock()
        self._finished = threading.Event()

    def start(self) -> Timer:
        manager = _get_manager()
        with self._lock:
            if self._started:
                msg = "timer already started"
                raise RuntimeError(msg)
            if self._cancelled:
                msg = "timer has been cancelled"
                raise RuntimeError(msg)
            self._started = True
            run_at = time.monotonic() + self._interval
        manager.schedule(self, run_at)
        return self

    def cancel(self) -> None:
        with self._lock:
            if self._cancelled or self._fired:
                return
            self._cancelled = True
            self._finished.set()

    def is_alive(self) -> bool:
        with self._lock:
            return self._started and not self._cancelled and not self._fired

    @property
    def finished(self) -> bool:
        return self._finished.is_set()

    def wait(self, timeout: float | None = None) -> bool:
        return self._finished.wait(timeout)

    def _fire(self) -> None:
        with self._lock:
            if self._cancelled or self._fired:
                return
            self._fired = True
        try:
            self.function(*self.args, **self.kwargs)
        except Exception:  # pragma: no cover - defensive logging
            logger.exception("Unhandled exception in timer callback")
        finally:
            self._finished.set()


@dataclass(order=True)
class _TimerEntry:
    run_at: float
    order: int = field(compare=False)
    timer: Timer = field(compare=False)


class _TimerManager:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._event = threading.Event()
        self._order_counter = itertools.count()
        self._timers: list[_TimerEntry] = []
        self._thread: threading.Thread | None = None
        self._check_interval = _DEFAULT_CHECK_INTERVAL

    def schedule(self, timer: Timer, run_at: float) -> None:
        with self._lock:
            heapq.heappush(
                self._timers,
                _TimerEntry(run_at, next(self._order_counter), timer),
            )
            self._ensure_thread_locked()
            self._event.set()

    def set_check_interval(self, interval: float) -> None:
        with self._lock:
            self._check_interval = interval
            self._event.set()

    def get_check_interval(self) -> float:
        with self._lock:
            return self._check_interval

    def _ensure_thread_locked(self) -> None:
        if self._thread is None:
            thread = threading.Thread(
                target=self._run,
                name="QuicklookTimerManager",
                daemon=True,
            )
            self._thread = thread
            thread.start()

    def _run(self) -> None:
        while True:
            wait_time = self._next_wait_duration()
            self._event.wait(wait_time)
            self._event.clear()
            now = time.monotonic()
            due: list[_TimerEntry] = []
            with self._lock:
                while self._timers and self._timers[0].run_at <= now:
                    due.append(heapq.heappop(self._timers))
            for entry in due:
                entry.timer._fire()

    def _next_wait_duration(self) -> float:
        with self._lock:
            check_interval = self._check_interval
            if not self._timers:
                return check_interval
            next_run = self._timers[0].run_at
        now = time.monotonic()
        return max(0.0, min(check_interval, next_run - now))


_manager: _TimerManager | None = None
_manager_lock = threading.Lock()


def _get_manager() -> _TimerManager:
    global _manager
    if _manager is None:
        with _manager_lock:
            if _manager is None:
                _manager = _TimerManager()
    return _manager
