from pathlib import Path

import pytest

from quicklook.generator.ccd_download import AdaptiveDownloadTimeout, CcdDownloadTimeoutError, download_ccd_to_path
from quicklook.types import CcdDataRef, CcdName, VisitName


def make_ref(ccd_name: str) -> CcdDataRef:
    return CcdDataRef(visit=VisitName("dummy:raw:broccoli"), ccd=CcdName(ccd_name))


class FakeClock:
    def __init__(self) -> None:
        self.now = 100.0

    def monotonic(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.now += seconds


class FakeDownloadOperation:
    def __init__(self, clock: FakeClock, *, finish_after: float | None, bytes_written: int) -> None:
        self._clock = clock
        self._finish_after = finish_after
        self._bytes_written = bytes_written
        self._started_at = clock.monotonic()
        self.terminated = False

    def is_finished(self) -> bool:
        if self.terminated or self._finish_after is None:
            return False
        return self._clock.monotonic() - self._started_at >= self._finish_after

    def result(self) -> int:
        if self.terminated:
            raise AssertionError("terminated operation has no result")
        return self._bytes_written

    def terminate(self) -> None:
        self.terminated = True


def test_adaptive_timeout_is_fixed_after_half_downloads() -> None:
    timeout = AdaptiveDownloadTimeout(total_downloads=5)

    timeout.record_success(make_ref("R00_S00"), 1.0)
    timeout.record_success(make_ref("R00_S01"), 2.0)
    assert timeout.timeout_seconds is None

    timeout.record_success(make_ref("R00_S02"), 3.0)
    assert timeout.timeout_seconds == pytest.approx(4.0)

    timeout.record_success(make_ref("R00_S03"), 99.0)
    assert timeout.timeout_seconds == pytest.approx(4.0)


def test_download_ccd_to_path_retries_once_after_timeout(tmp_path: Path) -> None:
    timeout = AdaptiveDownloadTimeout(total_downloads=2)
    timeout.record_success(make_ref("R00_S00"), 1.0)
    assert timeout.timeout_seconds == pytest.approx(2.0)

    clock = FakeClock()
    created_operations: list[FakeDownloadOperation] = []
    outpath = tmp_path / "ccd.fits"

    def start_operation(ref: CcdDataRef, path: Path) -> FakeDownloadOperation:
        if not created_operations:
            path.write_bytes(b"partial")
            operation = FakeDownloadOperation(clock, finish_after=None, bytes_written=5)
        else:
            path.write_bytes(b"complete")
            operation = FakeDownloadOperation(clock, finish_after=0.5, bytes_written=8)
        created_operations.append(operation)
        return operation

    result = download_ccd_to_path(
        make_ref("R00_S01"),
        outpath,
        timeout=timeout,
        start_operation=start_operation,
        monotonic=clock.monotonic,
        sleep=clock.sleep,
        poll_interval_seconds=0.5,
    )

    first, second = created_operations
    assert first.terminated
    assert not second.terminated
    assert result.bytes_written == 8
    assert result.elapsed == pytest.approx(0.5)
    assert outpath.read_bytes() == b"complete"


def test_download_ccd_to_path_raises_after_second_timeout(tmp_path: Path) -> None:
    timeout = AdaptiveDownloadTimeout(total_downloads=2)
    timeout.record_success(make_ref("R00_S00"), 1.0)

    clock = FakeClock()
    created_operations: list[FakeDownloadOperation] = []
    outpath = tmp_path / "ccd.fits"

    def start_operation(ref: CcdDataRef, path: Path) -> FakeDownloadOperation:
        path.write_bytes(b"partial")
        operation = FakeDownloadOperation(clock, finish_after=None, bytes_written=1)
        created_operations.append(operation)
        return operation

    with pytest.raises(CcdDownloadTimeoutError, match="attempt 2/2"):
        download_ccd_to_path(
            make_ref("R00_S02"),
            outpath,
            timeout=timeout,
            start_operation=start_operation,
            monotonic=clock.monotonic,
            sleep=clock.sleep,
            poll_interval_seconds=0.5,
        )

    first, second = created_operations
    assert first.terminated
    assert second.terminated
    assert not outpath.exists()
