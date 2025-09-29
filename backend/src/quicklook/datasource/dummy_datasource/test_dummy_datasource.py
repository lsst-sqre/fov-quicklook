from quicklook.datasource import get_datasource
from quicklook.types import VisitName


async def test_list_visit_ccds():
    visit = VisitName('raw:broccoli')
    ds = get_datasource()
    res = await ds.list_ccds(visit)
    assert len(res) > 0 # test時は少ない