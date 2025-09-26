import pytest

from quicklook.comm.generator import self_generator_id_context
from quicklook.types import CcdId, Visit

from quicklook.generator.generate_single_fits_tiles import generate_single_fits_tiles
from quicklook.generator.job import Job


@pytest.fixture(autouse=True, scope='module')
def set_generator_id():
    with self_generator_id_context():
        yield


@pytest.fixture
def broccoli_visit():
    return Visit('raw:broccoli')


def test_generate_single_fits_tiles(broccoli_visit: Visit):
    job = Job(visit=broccoli_visit)
    ccd_id = CcdId(broccoli_visit, 'R00_SG0')
    generate_single_fits_tiles(job, ccd_id)
