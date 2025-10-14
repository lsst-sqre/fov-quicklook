import pytest

from quicklook.comm.generator import set_generator_id_for_test
from quicklook.generator.generate_single_fits_tiles import (
    generate_single_fits_tiles,
    generate_single_fits_tiles_pipeline,
)
from quicklook.job.job import Job
from quicklook.types import CcdDataRef, CcdName, VisitName


@pytest.fixture(autouse=True, scope='module')
def set_generator_id():
    with set_generator_id_for_test():
        yield


@pytest.fixture
def broccoli_visit() -> VisitName:
    return VisitName('raw:broccoli')


def test_generate_single_fits_tiles(broccoli_visit: VisitName):
    job = Job(visit=broccoli_visit)
    ccd_ref = CcdDataRef(visit=broccoli_visit, ccd=CcdName('R00_SG0'))
    for _ in generate_single_fits_tiles(job, ccd_ref):
        pass


def test_generate_single_fits_tiles_pipeline(broccoli_visit: VisitName):
    job = Job(visit=broccoli_visit)
    ccd_refs = [
        CcdDataRef(visit=broccoli_visit, ccd=CcdName('R00_SG0')),
        CcdDataRef(visit=broccoli_visit, ccd=CcdName('R00_SG1')),
    ]
    for _ in generate_single_fits_tiles_pipeline(job, ccd_refs):
        print(_)
