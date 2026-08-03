from __future__ import annotations

import argparse
import fcntl
import json
import shlex
import shutil
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Iterable, Iterator, Sequence

import boto3
from botocore.client import Config as BotoConfig
from botocore.exceptions import ClientError
from lsst.daf.butler import Butler, Config, DatasetType

from quicklook.config import ButlerScopeConfig, config
from quicklook.datasource.butler_datasource.instrument import Instrument
from quicklook.review_app.synthetic import render_virtual_raw_fits_bytes, review_projection_ccd_names
from quicklook.types import CcdName, VisitName
from quicklook.utils.s3 import NoSuchKey, S3Config, s3_delete_objects_with_prefix, s3_download_object, s3_upload_object

FIXTURE_VERSION = "20260721-v8"
FIXTURE_REPOSITORY_NAME = "reviewapp-ci"
FIXTURE_MANIFEST_KEY = "_fixtures/review-app/sample-manifest.json"
FIXTURE_VERSION_KEY = "_fixtures/review-app/version.txt"
FIXTURE_COLLECTION = "LSSTCam/raw/all"
FIXTURE_RUN = "u/review-app-fixtures/raw"
DEFAULT_DUMMY_VISIT_COUNT = 50
DEFAULT_BUTLER_VISIT_COUNT = 2000
DEFAULT_CCDS = review_projection_ccd_names()


def _log_progress(message: str) -> None:
    print(f"[shared-fixtures] {message}", flush=True)


def _should_log_loop_progress(index: int, total: int) -> bool:
    return total <= 20 or index == 1 or index == total or index % 100 == 0


@dataclass(frozen=True)
class FixtureVisit:
    exposure_id: int
    day_obs: int
    physical_filter: str
    exposure_time: float
    target_name: str
    science_program: str
    observation_type: str = "science"
    observation_reason: str = "review-app"

    @property
    def obs_id(self) -> str:
        return f"fixture-{self.exposure_id}"

    @property
    def group_name(self) -> str:
        return f"fixture-group-{self.exposure_id}"

    @property
    def utc_start(self) -> datetime:
        offset = self.exposure_id - 910001
        base = datetime.strptime(str(self.day_obs), "%Y%m%d").replace(hour=3, tzinfo=timezone.utc)
        return base + timedelta(minutes=offset % 50, seconds=(offset * 7) % 60)

    @property
    def dummy_visit_id(self) -> str:
        return str(
            VisitName.from_parts(
                repository_name=FIXTURE_REPOSITORY_NAME,
                collection=FIXTURE_COLLECTION,
                dataset_type='raw',
                dimensions={'exposure': self.exposure_id},
            )
        )

    def manifest_entry(self, ccd_names: Sequence[CcdName]) -> dict[str, object]:
        entry = {
            "id": self.dummy_visit_id,
            "day_obs": self.day_obs,
            "physical_filter": self.physical_filter,
            "obs_id": self.obs_id,
            "exposure_time": self.exposure_time,
            "science_program": self.science_program,
            "observation_type": self.observation_type,
            "observation_reason": self.observation_reason,
            "target_name": self.target_name,
            "ccds": [str(ccd) for ccd in ccd_names],
        }
        return entry


@dataclass(frozen=True)
class SharedFixturePaths:
    root: Path
    lock_path: Path
    version_path: Path
    info_path: Path
    dummy_s3_root: Path
    manifest_path: Path
    marker_path: Path
    butler_root: Path
    butler_repo_root: Path
    data_repos_path: Path
    dummy_env_path: Path
    butler_env_path: Path

    @classmethod
    def from_root(cls, root: Path) -> "SharedFixturePaths":
        return cls(
            root=root,
            lock_path=root.parent / f".{root.name}.lock",
            version_path=root / "VERSION",
            info_path=root / "fixture-info.json",
            dummy_s3_root=root / "dummy-s3",
            manifest_path=root / "dummy-s3" / FIXTURE_MANIFEST_KEY,
            marker_path=root / "dummy-s3" / FIXTURE_VERSION_KEY,
            butler_root=root / "butler",
            butler_repo_root=root / "butler" / "repo",
            data_repos_path=root / "butler" / "data-repos.yaml",
            dummy_env_path=root / "dummy.env",
            butler_env_path=root / "butler.env",
        )


def default_fixture_visits(count: int = DEFAULT_DUMMY_VISIT_COUNT) -> list[FixtureVisit]:
    filters = ("u", "g", "r", "i", "z", "y")
    science_programs = (
        "review-app-wide",
        "review-app-deep",
        "review-app-calibration",
        "review-app-engineering",
        "review-app-nightly",
    )
    observation_reasons = (
        "survey",
        "targeted",
        "focus",
        "calibration",
        "engineering",
        "nightly",
    )
    observation_types = ("science", "science", "science", "acq", "flat", "focus")
    targets = (
        "spring-field",
        "summer-field",
        "autumn-field",
        "winter-field",
        "orion-cloud",
        "andromeda-arc",
        "southern-deep",
    )
    visits: list[FixtureVisit] = []
    for i in range(count):
        exposure_id = 910001 + i
        visits.append(
            FixtureVisit(
                exposure_id=exposure_id,
                day_obs=20260501 + i // 50,
                physical_filter=filters[i % len(filters)],
                exposure_time=(15.0, 20.0, 30.0, 45.0, 60.0)[i % 5],
                target_name=f"{targets[i % len(targets)]}-{(i // len(targets)) + 1}",
                science_program=science_programs[(i // len(filters)) % len(science_programs)],
                observation_type=observation_types[(i + i // len(filters)) % len(observation_types)],
                observation_reason=observation_reasons[
                    (i // (len(filters) * len(science_programs))) % len(observation_reasons)
                ],
            )
        )
    return visits


def default_butler_ccd_names() -> tuple[CcdName, ...]:
    return review_projection_ccd_names()


def build_fixture_config(repository_name: str = FIXTURE_REPOSITORY_NAME) -> list[dict[str, object]]:
    return [
        ButlerScopeConfig(
            dataset_type="raw",
            display_name="Raw (CI fixture)",
            collection=FIXTURE_COLLECTION,
            repository_name=repository_name,
            instrument="LSSTCam",
        )
        .model_dump()
    ]


def prepare_shared_fixtures(
    root: Path,
    *,
    version: str = FIXTURE_VERSION,
    repository_name: str = FIXTURE_REPOSITORY_NAME,
    ccd_names: Sequence[CcdName] | None = None,
    visits: Sequence[FixtureVisit] | None = None,
    butler_ccd_names: Sequence[CcdName] | None = None,
    butler_visits: Sequence[FixtureVisit] | None = None,
    butler_registry_url: str | None = None,
    overwrite: bool = False,
) -> SharedFixturePaths:
    visits_were_provided = visits is not None
    ccds_were_provided = ccd_names is not None
    if visits is None:
        visits = list(default_fixture_visits(DEFAULT_DUMMY_VISIT_COUNT))
        if butler_visits is None:
            butler_visits = list(default_fixture_visits(DEFAULT_BUTLER_VISIT_COUNT))
    else:
        visits = list(visits)
        if butler_visits is None:
            butler_visits = list(visits)
    if ccd_names is None:
        ccd_names = list(DEFAULT_CCDS)
    if butler_ccd_names is None:
        if visits_were_provided or ccds_were_provided:
            butler_ccd_names = list(ccd_names)
        else:
            butler_ccd_names = list(default_butler_ccd_names())

    paths = SharedFixturePaths.from_root(root)
    root.parent.mkdir(parents=True, exist_ok=True)

    _log_progress(
        f"prepare start root={root} dummy_visits={len(visits)} dummy_ccds={len(ccd_names)} "
        f"butler_visits={len(butler_visits)} butler_ccds={len(butler_ccd_names)} overwrite={overwrite}"
    )
    with _exclusive_lock(paths.lock_path):
        _log_progress(f"acquired lock {paths.lock_path}")
        if not overwrite and _is_fixture_ready(paths, version):
            _log_progress(f"fixture already ready at {paths.root}")
            if butler_registry_url is not None:
                _log_progress("refreshing Butler fixture for requested registry URL")
                _write_butler_fixture(
                    paths,
                    repository_name=repository_name,
                    ccd_names=butler_ccd_names,
                    visits=butler_visits,
                    butler_registry_url=butler_registry_url,
                )
                _write_path_dependent_files(
                    paths,
                    version=version,
                    repository_name=repository_name,
                    ccd_names=ccd_names,
                    visits=visits,
                    butler_ccd_names=butler_ccd_names,
                    butler_visits=butler_visits,
                    butler_registry_url=butler_registry_url,
                )
                _log_progress("rewrote Butler path-dependent files")
            return paths

        with TemporaryDirectory(dir=root.parent, prefix=f".{root.name}-") as staging_dir:
            staging_root = Path(staging_dir) / root.name
            stage_paths = SharedFixturePaths.from_root(staging_root)
            _log_progress(f"building fixture in staging dir {staging_root}")
            _write_local_fixture(
                stage_paths,
                version=version,
                repository_name=repository_name,
                ccd_names=ccd_names,
                visits=visits,
                butler_ccd_names=butler_ccd_names,
                butler_visits=butler_visits,
                butler_registry_url=butler_registry_url,
            )

            if root.exists():
                _log_progress(f"replacing existing fixture contents under {root}")
                _replace_directory_contents(root, staging_root)
            else:
                _log_progress(f"moving staged fixture into place at {root}")
                staging_root.replace(root)
            final_paths = SharedFixturePaths.from_root(root)
            _write_path_dependent_files(
                final_paths,
                version=version,
                repository_name=repository_name,
                ccd_names=ccd_names,
                visits=visits,
                butler_ccd_names=butler_ccd_names,
                butler_visits=butler_visits,
                butler_registry_url=butler_registry_url,
            )
            _log_progress(f"fixture ready at {root}")

    return SharedFixturePaths.from_root(root)


def _replace_directory_contents(target_root: Path, source_root: Path) -> None:
    target_root.mkdir(parents=True, exist_ok=True)

    for child in target_root.iterdir():
        if child.is_dir() and not child.is_symlink():
            shutil.rmtree(child)
        else:
            child.unlink()

    for child in source_root.iterdir():
        shutil.move(str(child), str(target_root / child.name))


def sync_dummy_fixture_to_s3(paths: SharedFixturePaths, s3_config: S3Config) -> None:
    _log_progress(f"syncing dummy fixture to s3 bucket={s3_config.bucket}")
    ensure_bucket_exists(s3_config)

    try:
        current_version = s3_download_object(s3_config, FIXTURE_VERSION_KEY).decode("utf-8").strip()
    except NoSuchKey:
        current_version = None

    wanted_version = paths.version_path.read_text().strip()
    if current_version == wanted_version:
        _log_progress(f"s3 already up to date version={wanted_version}")
        return

    _log_progress("deleting previous raw/ objects from s3")
    s3_delete_objects_with_prefix(s3_config, "raw/")

    files = [path for path in sorted(paths.dummy_s3_root.rglob("*")) if path.is_file()]
    for index, path in enumerate(files, start=1):
        key = path.relative_to(paths.dummy_s3_root).as_posix()
        _log_progress(f"uploading {index}/{len(files)} {key}")
        s3_upload_object(
            s3_config,
            key,
            path.read_bytes(),
            _content_type_for_path(path),
        )


def ensure_bucket_exists(s3_config: S3Config) -> None:
    client = boto3.client(
        "s3",
        endpoint_url=f"{'https' if s3_config.secure else 'http'}://{s3_config.endpoint}",
        aws_access_key_id=s3_config.access_key,
        aws_secret_access_key=s3_config.secret_key,
        config=BotoConfig(
            signature_version="s3v4",
            tcp_keepalive=True,
            request_checksum_calculation="when_required",
            response_checksum_validation="when_required",
            s3={"addressing_style": "path"},
        ),
    )
    try:
        client.head_bucket(Bucket=s3_config.bucket)
    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code")
        if error_code not in {"404", "NoSuchBucket"}:
            raise
        client.create_bucket(Bucket=s3_config.bucket)


def _is_fixture_ready(paths: SharedFixturePaths, version: str) -> bool:
    if not paths.root.exists():
        return False
    if not paths.version_path.exists():
        return False
    if paths.version_path.read_text().strip() != version:
        return False
    required = [
        paths.manifest_path,
        paths.marker_path,
        paths.data_repos_path,
        paths.dummy_env_path,
        paths.butler_env_path,
        paths.info_path,
        paths.butler_repo_root / "butler.yaml",
    ]
    return all(path.exists() for path in required)


def _write_local_fixture(
    paths: SharedFixturePaths,
    *,
    version: str,
    repository_name: str,
    ccd_names: Sequence[CcdName],
    visits: Sequence[FixtureVisit],
    butler_ccd_names: Sequence[CcdName],
    butler_visits: Sequence[FixtureVisit],
    butler_registry_url: str | None,
) -> None:
    paths.root.mkdir(parents=True, exist_ok=True)
    _log_progress("writing dummy fixture files")
    _write_dummy_fixture(paths, version=version, ccd_names=ccd_names, visits=visits)
    _log_progress("writing Butler fixture")
    _write_butler_fixture(
        paths,
        repository_name=repository_name,
        ccd_names=butler_ccd_names,
        visits=butler_visits,
        butler_registry_url=butler_registry_url,
    )
    paths.version_path.write_text(f"{version}\n")
    _log_progress("writing env/info files")
    _write_path_dependent_files(
        paths,
        version=version,
        repository_name=repository_name,
        ccd_names=ccd_names,
        visits=visits,
        butler_ccd_names=butler_ccd_names,
        butler_visits=butler_visits,
        butler_registry_url=butler_registry_url,
    )


def _write_path_dependent_files(
    paths: SharedFixturePaths,
    *,
    version: str,
    repository_name: str,
    ccd_names: Sequence[CcdName],
    visits: Sequence[FixtureVisit],
    butler_ccd_names: Sequence[CcdName],
    butler_visits: Sequence[FixtureVisit],
    butler_registry_url: str | None,
) -> None:
    _write_data_repos(paths, repository_name=repository_name)
    _write_env_files(paths, repository_name=repository_name)
    paths.info_path.write_text(
        json.dumps(
            {
                "version": version,
                "repository_name": repository_name,
                "collection": FIXTURE_COLLECTION,
                "dummy": {
                    "ccd_names": [str(ccd) for ccd in ccd_names],
                    "visit_count": len(visits),
                    "visits": [visit.manifest_entry(ccd_names) for visit in visits],
                },
                "butler": {
                    "ccd_names": [str(ccd) for ccd in butler_ccd_names],
                    "visit_count": len(butler_visits),
                    "registry_backend": "postgresql" if butler_registry_url else "sqlite",
                },
                "paths": {
                    "dummy_env": str(paths.dummy_env_path),
                    "butler_env": str(paths.butler_env_path),
                    "data_repos": str(paths.data_repos_path),
                    "manifest": str(paths.manifest_path),
                },
            },
            indent=2,
        )
    )


def _write_dummy_fixture(
    paths: SharedFixturePaths,
    *,
    version: str,
    ccd_names: Sequence[CcdName],
    visits: Sequence[FixtureVisit],
) -> None:
    paths.manifest_path.parent.mkdir(parents=True, exist_ok=True)
    _log_progress(f"writing dummy manifest with {len(visits)} visits")
    manifest = {
        "version": version,
        "visits": [visit.manifest_entry(ccd_names) for visit in visits],
    }
    paths.manifest_path.write_text(json.dumps(manifest, indent=2))
    paths.marker_path.parent.mkdir(parents=True, exist_ok=True)
    paths.marker_path.write_text(f"{version}\n")

    if not visits:
        _log_progress("dummy fixture has no visits; skipping FITS generation")
        return

    shared_visit = visits[0]
    for detector_index, ccd_name in enumerate(ccd_names, start=1):
        output_path = paths.dummy_s3_root / "raw" / str(shared_visit.exposure_id) / f"{ccd_name}.fits"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        _log_progress(f"generating shared dummy FITS {detector_index}/{len(ccd_names)} ccd={ccd_name}")
        seed = shared_visit.exposure_id * 100 + detector_index
        output_path.write_bytes(generate_raw_fits_bytes(ccd_name, seed=seed, visit=shared_visit))


def _write_butler_fixture(
    paths: SharedFixturePaths,
    *,
    repository_name: str,
    ccd_names: Sequence[CcdName],
    visits: Sequence[FixtureVisit],
    butler_registry_url: str | None,
) -> None:
    paths.butler_repo_root.parent.mkdir(parents=True, exist_ok=True)
    _log_progress(
        f"initializing Butler repo visits={len(visits)} ccds={len(ccd_names)} "
        f"registry={'postgresql' if butler_registry_url else 'sqlite'}"
    )
    if butler_registry_url is not None:
        Butler.makeRepo(
            paths.butler_repo_root,
            config=Config({"registry": {"db": butler_registry_url}}),
            forceConfigRoot=False,
            overwrite=True,
        )
    else:
        Butler.makeRepo(paths.butler_repo_root, overwrite=True)

    butler = Butler.from_config(paths.butler_repo_root, writeable=True)
    registry = butler.registry
    universe = butler.dimensions
    instrument = Instrument.get("LSSTCam")

    detector_ids = {ccd_name: instrument.ccd_2_detector[ccd_name] for ccd_name in ccd_names}
    _log_progress(f"registering {len(detector_ids)} Butler detectors")
    registry.insertDimensionData(
        "instrument",
        {
            "name": "LSSTCam",
            "visit_max": 10_000_000,
            "visit_system": 1,
            "exposure_max": 10_000_000,
            "detector_max": max(detector_ids.values()) + 1,
            "class_name": "quicklook.review_app.synthetic.LSSTCam",
        },
    )

    for ccd_name, detector_id in detector_ids.items():
        raft, slot = str(ccd_name).split("_")
        registry.insertDimensionData(
            "detector",
            {
                "instrument": "LSSTCam",
                "id": detector_id,
                "full_name": str(ccd_name),
                "name_in_raft": slot,
                "raft": raft,
                "purpose": "SCIENCE",
            },
        )

    raw_dataset = DatasetType(
        "raw",
        dimensions=("instrument", "detector", "exposure"),
        storageClass="StructuredDataDict",
        universe=universe,
    )
    registry.registerDatasetType(raw_dataset)
    registry.registerCollection(FIXTURE_COLLECTION)
    registry.registerRun(FIXTURE_RUN)

    registered_filters: set[str] = set()
    registered_days: set[int] = set()

    for index, visit in enumerate(visits, start=1):
        if _should_log_loop_progress(index, len(visits)):
            _log_progress(f"registering Butler exposure {index}/{len(visits)} id={visit.exposure_id}")
        if visit.physical_filter not in registered_filters:
            registry.insertDimensionData(
                "physical_filter",
                {
                    "instrument": "LSSTCam",
                    "name": visit.physical_filter,
                    "band": visit.physical_filter,
                },
            )
            registered_filters.add(visit.physical_filter)
        if visit.day_obs not in registered_days:
            registry.insertDimensionData("day_obs", {"instrument": "LSSTCam", "id": visit.day_obs})
            registered_days.add(visit.day_obs)

        registry.insertDimensionData("group", {"instrument": "LSSTCam", "name": visit.group_name})
        registry.insertDimensionData(
            "exposure",
            {
                "instrument": "LSSTCam",
                "id": visit.exposure_id,
                "day_obs": visit.day_obs,
                "group": visit.group_name,
                "physical_filter": visit.physical_filter,
                "obs_id": visit.obs_id,
                "exposure_time": visit.exposure_time,
                "observation_type": visit.observation_type,
                "observation_reason": visit.observation_reason,
                "seq_num": 1,
                "seq_start": 1,
                "seq_end": 1,
                "target_name": visit.target_name,
                "science_program": visit.science_program,
            },
        )

        refs = registry.insertDatasets(
            raw_dataset,
            dataIds=[
                {"instrument": "LSSTCam", "detector": detector_ids[ccd_name], "exposure": visit.exposure_id}
                for ccd_name in ccd_names
            ],
            run=FIXTURE_RUN,
        )
        registry.associate(FIXTURE_COLLECTION, refs)
    _log_progress("Butler fixture registration finished")

def _write_env_files(paths: SharedFixturePaths, *, repository_name: str) -> None:
    paths.dummy_env_path.write_text(
        "\n".join(
            [
                "# shellcheck shell=sh",
                _shell_env_assignment("QUICKLOOK_data_source", "dummy"),
                "",
            ]
        )
    )


def _write_data_repos(paths: SharedFixturePaths, *, repository_name: str) -> None:
    paths.data_repos_path.write_text(
        f"{repository_name}: file://{(paths.butler_repo_root / 'butler.yaml').resolve()}\n"
    )
    paths.butler_env_path.write_text(
        "\n".join(
            [
                "# shellcheck shell=sh",
                _shell_env_assignment("DAF_BUTLER_REPOSITORY_INDEX", str(paths.data_repos_path)),
                _shell_env_assignment("QUICKLOOK_data_source", "butler"),
                _shell_env_assignment(
                    "QUICKLOOK_ccd_data_types",
                    json.dumps(build_fixture_config(repository_name), ensure_ascii=False),
                ),
                "",
            ]
        )
    )


def _shell_env_assignment(name: str, value: str) -> str:
    return f"{name}={shlex.quote(value)}"


def generate_raw_fits_bytes(ccd_name: CcdName, *, seed: int, visit: FixtureVisit) -> bytes:
    del seed
    return render_virtual_raw_fits_bytes(
        ccd_name=ccd_name,
        exposure_id=visit.exposure_id,
        day_obs=visit.day_obs,
        physical_filter=visit.physical_filter,
        obs_id=visit.obs_id,
    )


def _content_type_for_path(path: Path) -> str:
    if path.suffix == ".json":
        return "application/json"
    if path.suffix == ".txt":
        return "text/plain"
    if path.suffix == ".fits":
        return "application/fits"
    return "application/octet-stream"


@contextmanager
def _exclusive_lock(lock_path: Path) -> Iterator[None]:
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("w") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(f, fcntl.LOCK_UN)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prepare shared review app fixtures.")
    parser.add_argument("--root", type=Path, required=True, help="Persistent root directory for shared fixtures")
    parser.add_argument("--version", default=FIXTURE_VERSION, help="Fixture version marker")
    parser.add_argument("--repository-name", default=FIXTURE_REPOSITORY_NAME, help="Butler repository alias name")
    parser.add_argument(
        "--visit-count",
        type=int,
        default=DEFAULT_DUMMY_VISIT_COUNT,
        help="Number of materialized dummy visits to generate",
    )
    parser.add_argument(
        "--butler-visit-count",
        type=int,
        default=DEFAULT_BUTLER_VISIT_COUNT,
        help="Number of Butler catalog visits to generate",
    )
    parser.add_argument(
        "--ccd",
        action="append",
        default=None,
        help="CCD name to include. May be specified multiple times. Default: review projection central 3x3 (R22_S00..R22_S22)",
    )
    parser.add_argument(
        "--butler-ccd",
        action="append",
        default=None,
        help="CCD name to register in the Butler catalog. Default: the central 3x3 CCDs in raft R22",
    )
    parser.add_argument(
        "--butler-registry-url",
        default=None,
        help="Optional SQLAlchemy URL for the Butler registry database",
    )
    parser.add_argument("--overwrite", action="store_true", help="Rebuild the local shared fixture root even if it exists")
    parser.add_argument(
        "--seed-s3",
        action="store_true",
        help="Upload the generated dummy sample tree into config.s3_test_data as well",
    )
    parser.add_argument(
        "--ensure-tile-bucket",
        action="store_true",
        help="Ensure config.s3_tile bucket exists before exiting",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> None:
    args = parse_args(argv)
    _log_progress("seed fixture command started")
    ccd_names = [CcdName(ccd) for ccd in args.ccd] if args.ccd else list(DEFAULT_CCDS)
    butler_ccd_names = [CcdName(ccd) for ccd in args.butler_ccd] if args.butler_ccd else list(default_butler_ccd_names())
    visits = default_fixture_visits(args.visit_count)
    butler_visits = default_fixture_visits(args.butler_visit_count)
    paths = prepare_shared_fixtures(
        args.root,
        version=args.version,
        repository_name=args.repository_name,
        ccd_names=ccd_names,
        visits=visits,
        butler_ccd_names=butler_ccd_names,
        butler_visits=butler_visits,
        butler_registry_url=args.butler_registry_url,
        overwrite=args.overwrite,
    )
    if args.ensure_tile_bucket:
        _log_progress("ensuring tile bucket exists")
        ensure_bucket_exists(config.s3_tile)
    if args.seed_s3:
        sync_dummy_fixture_to_s3(paths, config.s3_test_data)

    _log_progress("seed fixture command finished")
    print(json.dumps({"root": str(paths.root), "info": str(paths.info_path)}, indent=2))


if __name__ == "__main__":
    main()
