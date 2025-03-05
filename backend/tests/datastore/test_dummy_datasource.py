import pytest

from quicklook.datasource import get_datasource
from quicklook.types import Visit

pytestmark = pytest.mark.focus


def test_list_visit_ccds():
    visit = Visit.from_id('raw:broccoli')
    ds = get_datasource()
    res = ds.list_ccds(visit)
    assert len(res) == 205
