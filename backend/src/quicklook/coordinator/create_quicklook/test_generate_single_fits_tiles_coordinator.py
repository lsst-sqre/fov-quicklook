from quicklook.types import Progress

from .generate_single_fits_tiles_coordinator import _merge_generate_progress


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
