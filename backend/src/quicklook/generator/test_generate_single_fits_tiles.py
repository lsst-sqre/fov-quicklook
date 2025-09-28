import pytest

from quicklook.comm.generator import self_generator_id_context
from quicklook.generator.generate_single_fits_tiles import generate_single_fits_tiles
from quicklook.job.job import Job
from quicklook.types import CcdDataRef, CcdName, VisitName


@pytest.fixture(autouse=True, scope='module')
def set_generator_id():
    with self_generator_id_context():
        yield


@pytest.fixture
def broccoli_visit() -> VisitName:
    return VisitName('raw:broccoli')


def test_generate_single_fits_tiles(broccoli_visit: VisitName):
    job = Job(visit=broccoli_visit)
    ccd_ref = CcdDataRef(visit=broccoli_visit, ccd=CcdName('R00_SG0'))
    for _ in generate_single_fits_tiles(job, ccd_ref):
        pass
