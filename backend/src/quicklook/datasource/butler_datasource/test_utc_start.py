from datetime import timezone
from types import SimpleNamespace

from astropy.time import Time
import lsst.daf.butler as butler_module

from quicklook.datasource.butler_datasource import _record_utc_start_attr


def test_record_utc_start_attr_reads_butler_timespan_begin():
    record = SimpleNamespace(
        timespan=butler_module.Timespan(
            begin=Time('2026-05-01T12:34:56', scale='utc'),
            end=None,
        )
    )

    value = _record_utc_start_attr(record)

    assert value is not None
    assert value.tzinfo == timezone.utc
    assert value.isoformat() == '2026-05-01T12:34:56+00:00'
