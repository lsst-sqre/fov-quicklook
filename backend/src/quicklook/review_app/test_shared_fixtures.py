import json
import subprocess
from pathlib import Path
from types import SimpleNamespace

from lsst.daf.butler import Butler

from quicklook.review_app import shared_fixtures
from quicklook.review_app.shared_fixtures import (
    FIXTURE_COLLECTION,
    FIXTURE_REPOSITORY_NAME,
    DEFAULT_BUTLER_VISIT_COUNT,
    DEFAULT_DUMMY_VISIT_COUNT,
    default_fixture_visits,
    default_butler_ccd_names,
    prepare_shared_fixtures,
)


def test_prepare_shared_fixtures_creates_manifest_and_env_files(tmp_path):
    root = tmp_path / "fixtures"
    paths = prepare_shared_fixtures(root, visits=default_fixture_visits(2))

    manifest = json.loads(paths.manifest_path.read_text())
    info = json.loads(paths.info_path.read_text())
    assert manifest["version"]
    assert len(manifest["visits"]) == 2
    assert manifest["visits"][0]["ccds"] == [str(ccd) for ccd in default_butler_ccd_names()]
    assert paths.dummy_env_path.exists()
    assert paths.butler_env_path.exists()
    assert (paths.dummy_s3_root / "raw" / "910001" / "R22_S00.fits").exists()
    assert (paths.dummy_s3_root / "raw" / "910002" / "R22_S22.fits").exists()
    assert info["butler"]["visit_count"] == 2


def test_prepare_shared_fixtures_builds_queryable_butler_repo(tmp_path, monkeypatch):
    root = tmp_path / "fixtures"
    paths = prepare_shared_fixtures(root, visits=default_fixture_visits(2))

    monkeypatch.setenv("DAF_BUTLER_REPOSITORY_INDEX", str(paths.data_repos_path))
    butler = Butler(FIXTURE_REPOSITORY_NAME, instrument="LSSTCam", collections=[FIXTURE_COLLECTION])

    exposures = list(
        butler.registry.queryDimensionRecords(
            "exposure",
            datasets="raw",
            where="day_obs=20260501",
            collections=[FIXTURE_COLLECTION],
        )
    )
    refs = list(butler.query_datasets("raw", where="exposure=910001", collections=[FIXTURE_COLLECTION]))

    assert [record.id for record in exposures] == [910001, 910002]
    assert len(refs) == len(default_butler_ccd_names())


def test_prepare_shared_fixtures_defaults_to_large_butler_catalog(tmp_path, monkeypatch):
    root = tmp_path / "fixtures"
    paths = prepare_shared_fixtures(root)

    monkeypatch.setenv("DAF_BUTLER_REPOSITORY_INDEX", str(paths.data_repos_path))
    butler = Butler(FIXTURE_REPOSITORY_NAME, instrument="LSSTCam", collections=[FIXTURE_COLLECTION])

    exposure_count = len(list(butler.registry.queryDimensionRecords("exposure", datasets="raw", collections=[FIXTURE_COLLECTION])))
    refs = list(
        butler.query_datasets(
            "raw",
            where=f"exposure=910001",
            collections=[FIXTURE_COLLECTION],
        )
    )
    info = json.loads(paths.info_path.read_text())

    assert exposure_count == DEFAULT_BUTLER_VISIT_COUNT
    assert len(refs) == len(default_butler_ccd_names())
    assert info["dummy"]["visit_count"] == DEFAULT_DUMMY_VISIT_COUNT
    assert info["butler"]["visit_count"] == DEFAULT_BUTLER_VISIT_COUNT


def test_default_butler_ccd_names_uses_central_raft():
    assert shared_fixtures.DEFAULT_CCDS == default_butler_ccd_names()
    assert default_butler_ccd_names() == (
        "R22_S00",
        "R22_S01",
        "R22_S02",
        "R22_S10",
        "R22_S11",
        "R22_S12",
        "R22_S20",
        "R22_S21",
        "R22_S22",
    )


def test_prepare_shared_fixtures_uses_postgres_registry_config_when_requested(tmp_path, monkeypatch):
    root = tmp_path / "fixtures"
    paths = shared_fixtures.SharedFixturePaths.from_root(root)
    calls: list[tuple[Path, dict[str, object]]] = []

    class FakeRegistry:
        def insertDimensionData(self, *args, **kwargs):
            return None

        def registerDatasetType(self, *args, **kwargs):
            return None

        def registerCollection(self, *args, **kwargs):
            return None

        def registerRun(self, *args, **kwargs):
            return None

        def insertDatasets(self, *args, **kwargs):
            return [SimpleNamespace(dataId={"detector": 0})]

        def associate(self, *args, **kwargs):
            return None

    fake_butler = SimpleNamespace(
        registry=FakeRegistry(),
        dimensions=SimpleNamespace(conform=lambda dimensions: tuple(dimensions)),
    )

    def fake_make_repo(path, **kwargs):
        calls.append((path, kwargs))
        Path(path).mkdir(parents=True, exist_ok=True)
        (Path(path) / "butler.yaml").write_text("registry:\n  db: postgresql://quicklook:test@postgres:5432/butler_registry\n")

    monkeypatch.setattr(shared_fixtures.Butler, "makeRepo", fake_make_repo)
    monkeypatch.setattr(shared_fixtures.Butler, "from_config", lambda *args, **kwargs: fake_butler)
    monkeypatch.setattr(shared_fixtures, "DatasetType", lambda *args, **kwargs: object())

    shared_fixtures._write_butler_fixture(
        paths,
        repository_name=FIXTURE_REPOSITORY_NAME,
        ccd_names=[shared_fixtures.DEFAULT_CCDS[0]],
        visits=default_fixture_visits(1),
        butler_registry_url="postgresql://quicklook:test@postgres:5432/butler_registry",
    )

    assert calls
    assert calls[0][1]["forceConfigRoot"] is False
    assert calls[0][1]["overwrite"] is True
    assert calls[0][1]["config"]["registry"]["db"] == "postgresql://quicklook:test@postgres:5432/butler_registry"


def test_prepare_shared_fixtures_preserves_existing_root_directory(tmp_path):
    root = tmp_path / "fixtures"
    root.mkdir()
    sentinel = root / "stale.txt"
    sentinel.write_text("stale")
    original_inode = root.stat().st_ino

    prepare_shared_fixtures(root, visits=default_fixture_visits(2), overwrite=True)

    assert root.stat().st_ino == original_inode
    assert not sentinel.exists()
    assert (root / "VERSION").exists()


def test_prepare_shared_fixtures_writes_shell_safe_butler_env(tmp_path):
    root = tmp_path / "fixtures"
    paths = prepare_shared_fixtures(root, visits=default_fixture_visits(2))

    result = subprocess.run(
        [
            "sh",
            "-c",
            'set -a && . "$1" && set +a && python - <<\'PY\'\n'
            "import os\n"
            "print(os.environ['DAF_BUTLER_REPOSITORY_INDEX'])\n"
            "print(os.environ['QUICKLOOK_data_source'])\n"
            "print(os.environ['QUICKLOOK_ccd_data_types'])\n"
            "PY",
            "sh",
            str(paths.butler_env_path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    data_repos_path, data_source, ccd_data_types = result.stdout.strip().splitlines()
    assert data_repos_path == str(paths.data_repos_path)
    assert data_source == "butler"
    assert json.loads(ccd_data_types)[0]["repository_name"] == FIXTURE_REPOSITORY_NAME
