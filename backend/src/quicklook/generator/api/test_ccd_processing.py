import pytest

from quicklook.generator.api import ccd_processing
from quicklook.job.job import Job
from quicklook.types import VisitName


def test_validate_job_cache_version_accepts_matching_version(monkeypatch):
    monkeypatch.setattr(ccd_processing.config, 'tile_cache_schema_version', 4)

    ccd_processing.validate_job_cache_version(Job(VisitName('repo:raw:4242'), cache_version=4))


def test_validate_job_cache_version_rejects_mismatch(monkeypatch):
    monkeypatch.setattr(ccd_processing.config, 'tile_cache_schema_version', 4)

    with pytest.raises(RuntimeError, match='controller=3, generator=4'):
        ccd_processing.validate_job_cache_version(Job(VisitName('repo:raw:4242'), cache_version=3))
