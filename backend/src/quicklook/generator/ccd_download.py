from __future__ import annotations

import multiprocessing
import queue
import statistics
import threading
import time
import traceback
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Protocol

import quicklook.mylogging
from quicklook.datasource import get_datasource
from quicklook.types import CcdDataRef

logger = quicklook.mylogging.getLogger(__name__)

_DEFAULT_POLL_INTERVAL_SECONDS = 0.1
_MAX_DOWNLOAD_ATTEMPTS = 2
_BOOTSTRAP_DOWNLOAD_TIMEOUT_SECONDS = 60.0


class DownloadOperation(Protocol):
    def is_finished(self) -> bool:
        ...

    def result(self) -> int:
        ...

    def terminate(self) -> None:
        ...


@dataclass(frozen=True)
class DownloadedCcd:
    bytes_written: int
    elapsed: float
    download_done_time: float


class CcdDownloadTimeoutError(TimeoutError):
    def __init__(self, ref: CcdDataRef, *, elapsed: float, timeout_seconds: float, attempt: int):
        super().__init__(
            f"Timed out downloading {ref.ccd} after {elapsed:.3f}s "
            f"(limit {timeout_seconds:.3f}s, attempt {attempt}/{_MAX_DOWNLOAD_ATTEMPTS})"
        )
        self.ref = ref
        self.elapsed = elapsed
        self.timeout_seconds = timeout_seconds
        self.attempt = attempt


class AdaptiveDownloadTimeout:
    def __init__(self, *, total_downloads: int, bootstrap_timeout_seconds: float = _BOOTSTRAP_DOWNLOAD_TIMEOUT_SECONDS):
        if total_downloads <= 0:
            raise ValueError("total_downloads must be positive")
        if bootstrap_timeout_seconds <= 0:
            raise ValueError("bootstrap_timeout_seconds must be positive")
        self._sample_target = (total_downloads + 1) // 2
        self._durations: list[float] = []
        self._timeout_seconds: float | None = None
        self._bootstrap_timeout_seconds = bootstrap_timeout_seconds
        self._lock = threading.Lock()

    @property
    def sample_target(self) -> int:
        return self._sample_target

    @property
    def timeout_seconds(self) -> float | None:
        with self._lock:
            return self._timeout_seconds

    @property
    def active_timeout_seconds(self) -> float:
        with self._lock:
            return self._timeout_seconds or self._bootstrap_timeout_seconds

    def record_success(self, ref: CcdDataRef, elapsed: float) -> None:
        with self._lock:
            self._durations.append(elapsed)
            completed = len(self._durations)
            if self._timeout_seconds is not None or completed < self._sample_target:
                return
            median_seconds = float(statistics.median(self._durations))
            self._timeout_seconds = median_seconds * 2
            logger.warning(
                "Adaptive CCD download timeout fixed at %.3fs after %d/%d downloads "
                "(median %.3fs, latest=%s %.3fs)",
                self._timeout_seconds,
                completed,
                self._sample_target,
                median_seconds,
                ref.ccd,
                elapsed,
            )


@dataclass
class _DownloadWorkerResult:
    bytes_written: int | None = None
    error_type: str | None = None
    error_message: str | None = None
    traceback_text: str | None = None


def _download_to_file_worker(ref: CcdDataRef, outpath: str, result_queue: Any) -> None:
    try:
        data = get_datasource().get_data_sync(ref)
        bytes_written = Path(outpath).write_bytes(data)
        result_queue.put(_DownloadWorkerResult(bytes_written=bytes_written))
    except Exception as e:
        result_queue.put(
            _DownloadWorkerResult(
                error_type=type(e).__name__,
                error_message=str(e),
                traceback_text=traceback.format_exc(),
            )
        )


class _SubprocessDownloadOperation:
    def __init__(self, ref: CcdDataRef, outpath: Path):
        ctx = multiprocessing.get_context("spawn")
        self._queue = ctx.Queue(maxsize=1)
        self._process = ctx.Process(
            target=_download_to_file_worker,
            args=(ref, str(outpath), self._queue),
        )
        self._process.start()
        self._closed = False

    def is_finished(self) -> bool:
        return not self._process.is_alive()

    def result(self) -> int:
        self._process.join()
        try:
            result = self._queue.get(timeout=1.0)
        except queue.Empty as e:
            raise RuntimeError(f"Download worker exited without a result (exitcode={self._process.exitcode})") from e
        finally:
            self._close()
        if result.bytes_written is not None:
            return result.bytes_written
        error_type = result.error_type or "RuntimeError"
        error_message = result.error_message or "unknown download failure"
        details = result.traceback_text or ""
        raise RuntimeError(f"{error_type}: {error_message}\n{details}".rstrip())

    def terminate(self) -> None:
        if self._process.is_alive():
            self._process.terminate()
        self._process.join()
        self._close()

    def _close(self) -> None:
        if self._closed:
            return
        self._queue.close()
        self._process.close()
        self._closed = True


def _start_subprocess_download(ref: CcdDataRef, outpath: Path) -> DownloadOperation:
    return _SubprocessDownloadOperation(ref, outpath)


def download_ccd_to_path(
    ref: CcdDataRef,
    outpath: Path,
    *,
    timeout: AdaptiveDownloadTimeout,
    start_operation: Callable[[CcdDataRef, Path], DownloadOperation] = _start_subprocess_download,
    monotonic: Callable[[], float] = time.monotonic,
    sleep: Callable[[float], None] = time.sleep,
    poll_interval_seconds: float = _DEFAULT_POLL_INTERVAL_SECONDS,
) -> DownloadedCcd:
    last_timeout: CcdDownloadTimeoutError | None = None

    for attempt in range(1, _MAX_DOWNLOAD_ATTEMPTS + 1):
        started_at = monotonic()
        operation = start_operation(ref, outpath)
        try:
            bytes_written = _wait_for_download(
                ref,
                operation,
                started_at=started_at,
                attempt=attempt,
                timeout=timeout,
                monotonic=monotonic,
                sleep=sleep,
                poll_interval_seconds=poll_interval_seconds,
            )
        except CcdDownloadTimeoutError as e:
            last_timeout = e
            outpath.unlink(missing_ok=True)
            if attempt >= _MAX_DOWNLOAD_ATTEMPTS:
                raise
            logger.warning("%s; retrying once", e)
            continue

        elapsed = monotonic() - started_at
        timeout.record_success(ref, elapsed)
        return DownloadedCcd(
            bytes_written=bytes_written,
            elapsed=elapsed,
            download_done_time=monotonic(),
        )

    if last_timeout is None:  # pragma: no cover
        raise RuntimeError(f"Download attempts exhausted unexpectedly for {ref.ccd}")
    raise last_timeout


def _wait_for_download(
    ref: CcdDataRef,
    operation: DownloadOperation,
    *,
    started_at: float,
    attempt: int,
    timeout: AdaptiveDownloadTimeout,
    monotonic: Callable[[], float],
    sleep: Callable[[float], None],
    poll_interval_seconds: float,
) -> int:
    while not operation.is_finished():
        timeout_seconds = timeout.active_timeout_seconds
        elapsed = monotonic() - started_at
        if elapsed >= timeout_seconds:
            operation.terminate()
            raise CcdDownloadTimeoutError(
                ref,
                elapsed=elapsed,
                timeout_seconds=timeout_seconds,
                attempt=attempt,
            )
        sleep(poll_interval_seconds)
    return operation.result()
