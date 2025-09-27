import pytest

from quicklook.comm.generator import self_generator_id_context
from quicklook.config import config
from quicklook.generator.job import Job
from quicklook.generator.job_local_storage import JobLocalStorage
from quicklook.types import VisitName


@pytest.fixture(autouse=True, scope='module')
def set_generator_id():
    with self_generator_id_context():
        yield


@pytest.fixture(autouse=True)
def clear_job_local_storage_cache():
    JobLocalStorage.from_job.cache_clear()
    yield
    JobLocalStorage.from_job.cache_clear()


def test_logger_writes_to_base_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(config, 'job_local_dir', tmp_path)

    job = Job(visit=VisitName('raw:logger-test'))
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
