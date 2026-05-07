import json

from quicklook.datasource.dummy_datasource import DummyDataSource
from quicklook.datasource.types import Query
from quicklook.types import CcdDataType
from quicklook.datasource import get_datasource
from quicklook.types import VisitName


async def test_list_visit_ccds():
    visit = VisitName('dummy:raw:broccoli')
    ds = get_datasource()
    res = await ds.list_ccds(visit)
    assert len(res) > 0 # test時は少ない


def test_query_visits_uses_shared_manifest(monkeypatch):
    payload = json.dumps(
        {
            "version": "fixture",
            "visits": [
                {
                    "id": "dummy:raw:910001",
                    "day_obs": 20260501,
                    "physical_filter": "r",
                    "obs_id": "fixture-910001",
                    "exposure_time": 15.0,
                    "science_program": "review-app-fixtures",
                    "observation_type": "science",
                    "observation_reason": "review-app",
                    "target_name": "fixture-target-1",
                    "ccds": ["R01_S00", "R01_S01"],
                }
            ],
        }
    ).encode("utf-8")
    monkeypatch.setattr(
        "quicklook.datasource.dummy_datasource.s3_download_object",
        lambda *_args, **_kwargs: payload,
    )

    ds = DummyDataSource()
    visits = ds.query_visits_sync(Query(data_type=CcdDataType("raw"), repository_name="dummy", limit=10))

    assert [visit.id for visit in visits] == ["dummy:raw:910001"]


def test_get_exposure_data_types_uses_shared_manifest(monkeypatch):
    payload = json.dumps(
        {
            "version": "fixture",
            "visits": [
                {
                    "id": "dummy:raw:910001",
                    "day_obs": 20260501,
                    "physical_filter": "r",
                    "obs_id": "fixture-910001",
                    "exposure_time": 15.0,
                    "science_program": "review-app-fixtures",
                    "observation_type": "science",
                    "observation_reason": "review-app",
                    "target_name": "fixture-target-1",
                    "ccds": ["R01_S00", "R01_S01"],
                }
            ],
        }
    ).encode("utf-8")
    monkeypatch.setattr(
        "quicklook.datasource.dummy_datasource.s3_download_object",
        lambda *_args, **_kwargs: payload,
    )

    ds = DummyDataSource()
    assert ds.get_exposure_data_types_sync(910001) == [CcdDataType("dummy:raw")]
