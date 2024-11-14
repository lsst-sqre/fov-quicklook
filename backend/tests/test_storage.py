import pytest

from quicklook.storage import s3_list_visit_ccds
from quicklook.types import Visit

pytestmark = pytest.mark.focus


def test_list_visit_ccds():
    visit = Visit(
        name='broccoli',
        data_type='raw',
    )
    res = [*s3_list_visit_ccds(visit)]
    assert len(res) == 205
