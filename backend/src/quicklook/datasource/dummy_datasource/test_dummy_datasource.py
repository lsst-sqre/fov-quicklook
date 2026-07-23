from types import SimpleNamespace

from quicklook.config import ButlerScopeConfig, config
from quicklook.datasource.dummy_datasource import DummyDataSource
from quicklook.datasource.types import Query
from quicklook.datasource import get_datasource
from quicklook.review_app.shared_fixtures import DEFAULT_DUMMY_VISIT_COUNT
from quicklook.types import CcdDataType
from quicklook.types import VisitName

RAW_SCOPE = ButlerScopeConfig(
    dataset_type="raw",
    display_name="Raw",
    collection="LSSTCam/raw/all",
    repository_name="reviewapp-ci",
    instrument="LSSTCam",
)


async def test_list_visit_ccds(monkeypatch):
    monkeypatch.setattr(
        "quicklook.datasource.dummy_datasource.s3_list_objects",
        lambda *_args, **_kwargs: [SimpleNamespace(key="raw/910001/R22_S00.fits", type="file")],
    )
    visit = VisitName("reviewapp-ci:LSSTCam!-raw!-all:raw:exposure=910001")
    ds = get_datasource()
    res = await ds.list_ccds(visit)
    assert len(res) > 0 # test時は少ない


def test_query_visits_returns_generated_fixture_visits(monkeypatch):
    monkeypatch.setattr(config, "butler_scopes", [RAW_SCOPE])

    ds = DummyDataSource()
    visits = ds.query_visits_sync(
        Query(
            repository_name=RAW_SCOPE.repository_name,
            collection=RAW_SCOPE.collection,
            dataset_type=RAW_SCOPE.dataset_type,
            limit=DEFAULT_DUMMY_VISIT_COUNT,
        )
    )

    assert len(visits) == DEFAULT_DUMMY_VISIT_COUNT
    assert visits[0].id == "reviewapp-ci:LSSTCam!-raw!-all:raw:exposure=910001"
    assert visits[0].utc_start is not None
    assert visits[0].utc_start.isoformat() == "2026-05-01T03:00:00+00:00"
    assert visits[-1].id == "reviewapp-ci:LSSTCam!-raw!-all:raw:exposure=910050"


def test_query_visits_respects_offset(monkeypatch):
    monkeypatch.setattr(config, "butler_scopes", [RAW_SCOPE])

    ds = DummyDataSource()
    visits = ds.query_visits_sync(
        Query(
            repository_name=RAW_SCOPE.repository_name,
            collection=RAW_SCOPE.collection,
            dataset_type=RAW_SCOPE.dataset_type,
            limit=1,
            offset=1,
        )
    )

    assert [visit.id for visit in visits] == ["reviewapp-ci:LSSTCam!-raw!-all:raw:exposure=910002"]


def test_get_exposure_data_types_uses_generated_fixture_scope(monkeypatch):
    monkeypatch.setattr(config, "butler_scopes", [RAW_SCOPE])

    ds = DummyDataSource()
    assert ds.get_exposure_data_types_sync(910001) == [CcdDataType("reviewapp-ci:LSSTCam!-raw!-all:raw")]


def test_representative_uuid_round_trips_to_visit():
    ds = DummyDataSource()

    representative_uuid = ds.get_visit_representative_uuid_sync(VisitName("reviewapp-ci:LSSTCam!-raw!-all:raw:exposure=910001"))

    assert ds.resolve_visit_sync(VisitName(f"reviewapp-ci:by_uuid:{representative_uuid}")) == VisitName("reviewapp-ci:LSSTCam!-raw!-all:raw:exposure=910001")


def test_get_data_sync_reuses_single_shared_visit(monkeypatch):
    seen: list[str] = []

    def fake_download(_config, key: str, *_args, **_kwargs) -> bytes:
        seen.append(key)
        return b"fits"

    monkeypatch.setattr("quicklook.datasource.dummy_datasource.s3_download_object", fake_download)

    ds = DummyDataSource()
    data = ds.get_data_sync(
        ref=SimpleNamespace(
            visit=VisitName("reviewapp-ci:LSSTCam!-raw!-all:raw:exposure=910050"),
            ccd="R22_S00",
        )
    )

    assert data == b"fits"
    assert seen == ["raw/910001/R22_S00.fits"]


def test_list_ccds_sync_reuses_single_shared_visit(monkeypatch):
    seen: list[str] = []

    def fake_list(_config, *, prefix: str):
        seen.append(prefix)
        return [SimpleNamespace(key="raw/910001/R22_S00.fits", type="file")]

    monkeypatch.setattr("quicklook.datasource.dummy_datasource.s3_list_objects", fake_list)

    ds = DummyDataSource()
    ccds = ds.list_ccds_sync(VisitName("reviewapp-ci:LSSTCam!-raw!-all:raw:exposure=910050"))

    assert ccds == ["R22_S00"]
    assert seen == ["raw/910001/"]
