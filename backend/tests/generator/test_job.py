import pytest
from quicklook.generator.job.generate_single_fits_tiles import generate_single_fits_tiles
from quicklook.job import Job
from quicklook.types import CcdId, Visit


@pytest.fixture
def broccoli_visit():
    return Visit('raw:broccoli')


def test_generate_single_fits_tiles(broccoli_visit: Visit):
    job = Job(visit=broccoli_visit)
    ccd_id = CcdId(broccoli_visit, 'R00_SG0')
    generate_single_fits_tiles(job, ccd_id)
