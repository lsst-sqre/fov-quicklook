from __future__ import annotations

import json
import statistics
import subprocess
import sys
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Protocol

import quicklook.mylogging
from quicklook.types import CcdDataRef, CcdName, VisitName

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
    def __init__(self, visit: str, ccd_name: str, elapsed: float, timeout_seconds: float, attempt: int):
        self._pickle_args = (visit, ccd_name, elapsed, timeout_seconds, attempt)
        self.ref = CcdDataRef(visit=VisitName(visit), ccd=CcdName(ccd_name))
        self.elapsed = elapsed
        self.timeout_seconds = timeout_seconds
        self.attempt = attempt
        super().__init__(
            f"Timed out downloading {ccd_name} after {elapsed:.3f}s "
            f"(limit {timeout_seconds:.3f}s, attempt {attempt}/{_MAX_DOWNLOAD_ATTEMPTS})"
        )

    @classmethod
    def from_ref(
        cls,
        ref: CcdDataRef,
        *,
        elapsed: float,
        timeout_seconds: float,
        attempt: int,
    ) -> "CcdDownloadTimeoutError":
        return cls(
            str(ref.visit),
            str(ref.ccd),
            elapsed,
            timeout_seconds,
            attempt,
        )

    def __reduce__(self):
        return (type(self), self._pickle_args)


class AdaptiveDownloadTimeout:
    def __init__(
        self,
        *,
        total_downloads: int | None = None,
        sample_target: int | None = None,
        bootstrap_timeout_seconds: float = _BOOTSTRAP_DOWNLOAD_TIMEOUT_SECONDS,
    ):
        if total_downloads is not None and total_downloads <= 0:
            raise ValueError("total_downloads must be positive")
        if sample_target is None:
            if total_downloads is None:
                raise ValueError("total_downloads or sample_target must be provided")
            sample_target = (total_downloads + 1) // 2
        if sample_target <= 0:
            raise ValueError("sample_target must be positive")
        if bootstrap_timeout_seconds <= 0:
            raise ValueError("bootstrap_timeout_seconds must be positive")
        self._sample_target = sample_target
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


class _SubprocessDownloadOperation:
    def __init__(self, ref: CcdDataRef, outpath: Path):
        self._process = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "quicklook.generator.ccd_download_worker",
                str(ref.visit),
                str(ref.ccd),
                str(outpath),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        self._closed = False

    def is_finished(self) -> bool:
        return self._process.poll() is not None

    def result(self) -> int:
        stdout, stderr = self._process.communicate()
        self._close()
        try:
            result = json.loads(stdout or "{}")
        except json.JSONDecodeError as e:
            raise RuntimeError(
                f"Download worker returned invalid JSON (returncode={self._process.returncode}): {stderr or stdout}"
            ) from e
        if result.get("bytes_written") is not None and self._process.returncode == 0:
            return int(result["bytes_written"])
        error_type = result.get("error_type") or "RuntimeError"
        error_message = result.get("error_message") or stderr or "unknown download failure"
        details = result.get("traceback_text") or stderr or ""
        raise RuntimeError(f"{error_type}: {error_message}\n{details}".rstrip())

    def terminate(self) -> None:
        if self._process.poll() is None:
            self._process.terminate()
            self._process.wait(timeout=5)
        self._close()

    def _close(self) -> None:
        if self._closed:
            return
        if self._process.stdout is not None:
            self._process.stdout.close()
        if self._process.stderr is not None:
            self._process.stderr.close()
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
            raise CcdDownloadTimeoutError.from_ref(
                ref,
                elapsed=elapsed,
                timeout_seconds=timeout_seconds,
                attempt=attempt,
            )
        sleep(poll_interval_seconds)
    return operation.result()
