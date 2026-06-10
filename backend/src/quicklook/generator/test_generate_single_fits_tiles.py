import multiprocessing
import queue
import tempfile
from pathlib import Path

import pytest

from quicklook.comm.generator import set_generator_id_for_test
from quicklook.datasource import get_datasource
from quicklook.generator.generate_single_fits_tiles import (
    CcdMetadata,
    GenerateSingleFitsTilesProgress,
    ProcessCcdArgs,
    _process_ccd,
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
    return VisitName('dummy:raw:broccoli')


def test_process_ccd():
    visit = VisitName('dummy:raw:broccoli')
    ccd_name = CcdName('R01_S00')
    # visit = VisitName('dummy:calexp:192350')
    
    job = Job(visit=visit)

    ds = get_datasource()
    ref = CcdDataRef(visit=visit, ccd=ccd_name)

    data_bytes = ds.get_data_sync(ref)
    with tempfile.NamedTemporaryFile(delete=False) as f:
        f.write(data_bytes)
        f.flush()
        with multiprocessing.Manager() as manager:
            args = ProcessCcdArgs(
                job=job,
                ref=CcdDataRef(visit=visit, ccd=ccd_name),
                path=Path(f.name),
                progress=queue.Queue(),
                download_sem=manager.Semaphore(99),
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
    messages = list(generate_single_fits_tiles_pipeline(job, ccd_refs))

    assert any(isinstance(message, GenerateSingleFitsTilesProgress) for message in messages)
    assert any(isinstance(message, CcdMetadata) for message in messages)
