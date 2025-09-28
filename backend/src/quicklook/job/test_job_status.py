from os import terminal_size

import pytest

from quicklook.job.job import Job
from quicklook.job.job_status import JobStatus, display_status
from quicklook.types import CcdName, Progress, VisitName


@pytest.fixture
def sample_job() -> Job:
    return Job(visit=VisitName('dummy:raw:visit1'), id='job-1')


def test_display_status_multi_column_layout(capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch, sample_job: Job):
    monkeypatch.setattr('shutil.get_terminal_size', lambda fallback=None: terminal_size((120, 24)))

    status = JobStatus(sample_job)
    status.generate_single_fits_tiles = {
        CcdName('ccd1'): Progress(total=10, count=5),
        CcdName('ccd2'): Progress(total=10, count=8),
        CcdName('ccd3'): Progress(total=10, count=9),
    }

    display_status(status, columns=2)

    output = capsys.readouterr().out
    progress_lines = [line for line in output.splitlines() if '• ' in line and '[' in line]
    assert any('• ccd1' in line and '• ccd2' in line for line in progress_lines)
    assert any('• ccd3' in line for line in progress_lines)


def test_display_status_respects_requested_columns(capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch, sample_job: Job):
    monkeypatch.setattr('shutil.get_terminal_size', lambda fallback=None: terminal_size((180, 24)))

    status = JobStatus(sample_job)
    status.merge_tiles = {
        'g-1': Progress(total=5, count=1),
        'g-2': Progress(total=5, count=3),
        'g-3': Progress(total=5, count=5),
    }

    display_status(status, columns=3)

    output = capsys.readouterr().out
    progress_lines = [line for line in output.splitlines() if '• ' in line and '[' in line]
    first_row = next((line for line in progress_lines if '• g-1' in line), '')
    assert '• g-1' in first_row and '• g-2' in first_row and '• g-3' in first_row


def test_display_status_handles_empty_sections(capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch, sample_job: Job):
    monkeypatch.setattr('shutil.get_terminal_size', lambda fallback=None: terminal_size((100, 24)))

    status = JobStatus(sample_job)
    display_status(status, columns=1)

    output = capsys.readouterr().out
    assert '  (no entries)' in output
