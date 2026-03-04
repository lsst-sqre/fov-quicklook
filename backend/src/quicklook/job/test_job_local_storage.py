import pytest
import numpy

from quicklook.comm.generator import set_generator_id_for_test
from quicklook.config import config
from quicklook.job.job import Job
from quicklook.job.local_storage import JobLocalStorage
from quicklook.types import CcdName, Tile, TilePos, VisitName


@pytest.fixture(autouse=True, scope='module')
def set_generator_id():
    with set_generator_id_for_test():
        yield


def test_logger_writes_to_base_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(config, 'job_local_dir', tmp_path)

    job = Job(visit=VisitName('dummy:raw:logger-test'))
    storage = JobLocalStorage.from_job(job)

    logger = storage.logger
    message = 'JobLocalStorage log output test.'
    logger.info(message)
    for handler in logger.handlers:
        handler.flush()

    log_path = storage.base_dir / 'log'
    assert log_path.exists()
    assert message in log_path.read_text()

    for handler in list(logger.handlers):
        handler.close()
        logger.removeHandler(handler)

    storage.clear_all()


def test_load_local_merged_normalizes_legacy_2d_tile(tmp_path, monkeypatch):
    monkeypatch.setattr(config, 'job_local_dir', tmp_path)

    job = Job(visit=VisitName('dummy:raw:legacy-shape'))
    storage = JobLocalStorage.from_job(job)
    ccd_name = CcdName('R00_S00')
    pos = TilePos(level=0, i=0, j=0)
    legacy_data = numpy.array([[0.0, 2.0], [3.0, 0.0]], dtype=numpy.float32)

    storage.single_fits_tile.save(
        ccd_name,
        Tile(visit=job.visit, pos=pos, data=legacy_data),
    )

    merged = storage.single_fits_tile.load_local_merged(pos=pos, ccd_names=[ccd_name])

    assert merged.shape == (2, 2, 2)
    numpy.testing.assert_array_equal(merged[:, :, 0], legacy_data)
    numpy.testing.assert_array_equal(
        merged[:, :, 1],
        numpy.array([[0.0, 1.0], [1.0, 0.0]], dtype=numpy.float32),
    )

    storage.clear_all()


def test_load_local_merged_handles_mixed_legacy_and_alpha_tiles(tmp_path, monkeypatch):
    monkeypatch.setattr(config, 'job_local_dir', tmp_path)

    job = Job(visit=VisitName('dummy:raw:mixed-shape'))
    storage = JobLocalStorage.from_job(job)
    pos = TilePos(level=0, i=1, j=2)
    ccd_legacy = CcdName('R00_S00')
    ccd_alpha = CcdName('R00_S01')

    storage.single_fits_tile.save(
        ccd_legacy,
        Tile(
            visit=job.visit,
            pos=pos,
            data=numpy.array([[1.0, 0.0], [4.0, 0.0]], dtype=numpy.float32),
        ),
    )
    storage.single_fits_tile.save(
        ccd_alpha,
        Tile(
            visit=job.visit,
            pos=pos,
            data=numpy.array(
                [
                    [[10.0, 1.0], [20.0, 0.0]],
                    [[30.0, 0.5], [40.0, 1.0]],
                ],
                dtype=numpy.float32,
            ),
        ),
    )

    merged = storage.single_fits_tile.load_local_merged(pos=pos, ccd_names=[ccd_legacy, ccd_alpha])

    numpy.testing.assert_array_equal(
        merged[:, :, 0],
        numpy.array([[11.0, 20.0], [34.0, 40.0]], dtype=numpy.float32),
    )
    numpy.testing.assert_array_equal(
        merged[:, :, 1],
        numpy.array([[2.0, 0.0], [1.5, 1.0]], dtype=numpy.float32),
    )

    storage.clear_all()
