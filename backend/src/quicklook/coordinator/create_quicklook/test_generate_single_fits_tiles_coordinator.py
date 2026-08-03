import pytest

from quicklook.comm.types import GeneratorId, GeneratorInfo
from quicklook.generator.api.ccd_processing_protocol import ErrorMessage
from quicklook.job.job import Job
from quicklook.types import CcdName, Progress, VisitName

from .generate_single_fits_tiles_coordinator import _handle_generator_message, _merge_generate_progress, _record_assigned_ccd


def test_merge_generate_progress_keeps_higher_existing_ratio() -> None:
    existing = Progress(total=4, count=3)
    incoming = Progress(total=4, count=1)

    merged = _merge_generate_progress(existing, incoming)

    assert merged == Progress(total=4, count=3)


def test_merge_generate_progress_accepts_higher_incoming_ratio() -> None:
    existing = Progress(total=4, count=2)
    incoming = Progress(total=4, count=3)

    merged = _merge_generate_progress(existing, incoming)

    assert merged == Progress(total=4, count=3)


def test_merge_generate_progress_accepts_more_advanced_equal_ratio() -> None:
    existing = Progress(total=4, count=2)
    incoming = Progress(total=8, count=4)

    merged = _merge_generate_progress(existing, incoming)

    assert merged == Progress(total=8, count=4)


async def test_handle_generator_message_raises_on_error_message():
    job = Job(VisitName('repo:raw:4242'))

    with pytest.raises(RuntimeError, match='generator-1'):
        await _handle_generator_message(
            ErrorMessage(ccd_name=None, error='cache version mismatch'),
            job,
            dispatcher=None,  # type: ignore[arg-type]
            generator=GeneratorInfo(id=GeneratorId('generator-1'), host='generator-host', port=9502),
            ws=None,  # type: ignore[arg-type]
            pending_wait_tasks=[],
        )


async def test_record_assigned_ccd_initializes_zero_progress():
    job = Job(VisitName('repo:raw:4242'))

    await _record_assigned_ccd(job, CcdName('R11_S00'))

    assert job.status.generate_single_fits_tiles == {
        CcdName('R11_S00'): Progress(total=4, count=0),
    }
