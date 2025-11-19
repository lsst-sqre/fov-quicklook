import queue
import tempfile
from pathlib import Path

import pytest

from quicklook.comm.generator import set_generator_id_for_test
from quicklook.datasource import get_datasource
from quicklook.generator.generate_single_fits_tiles import ProcessCcdArgs, _process_ccd, generate_single_fits_tiles_pipeline  # generate_single_fits_tiles,
from quicklook.job.job import Job
from quicklook.types import CcdDataRef, CcdName, VisitName


@pytest.fixture(autouse=True, scope='module')
def set_generator_id():
    with set_generator_id_for_test():
        yield


@pytest.fixture
def broccoli_visit() -> VisitName:
    return VisitName('raw:broccoli')


def test_process_ccd():
    visit = VisitName('raw:broccoli')
    ccd_name = CcdName('R01_S00')
    # visit = VisitName('calexp:192350')
    
    job = Job(visit=visit)

    ds = get_datasource()
    ref = CcdDataRef(visit=visit, ccd=ccd_name)

    data_bytes = ds.get_data_sync(ref)
    with tempfile.NamedTemporaryFile(delete=False) as f:
        f.write(data_bytes)
        f.flush()
        args = ProcessCcdArgs(
            job=job,
            ref=CcdDataRef(visit=visit, ccd=ccd_name),
            path=Path(f.name),
            progress=queue.Queue(),
        )
        _process_ccd(args)


# def test_generate_single_fits_tiles(broccoli_visit: VisitName):
#     job = Job(visit=broccoli_visit)
#     ccd_ref = CcdDataRef(visit=broccoli_visit, ccd=CcdName('R00_SG0'))
#     for _ in generate_single_fits_tiles(job, ccd_ref):
#         pass


def test_generate_single_fits_tiles_pipeline(broccoli_visit: VisitName):
    job = Job(visit=broccoli_visit)
    ccd_refs = [
        CcdDataRef(visit=broccoli_visit, ccd=CcdName('R00_SG0')),
        CcdDataRef(visit=broccoli_visit, ccd=CcdName('R00_SG1')),
    ]
    items = [(job, ref) for ref in ccd_refs]
    for _ in generate_single_fits_tiles_pipeline(items):
        print(_)
