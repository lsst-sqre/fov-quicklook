import pytest

from quicklook.comm.generator import set_generator_id_for_test
from quicklook.config import config
from quicklook.job.job import Job
from quicklook.job.local_storage import JobLocalStorage
from quicklook.types import VisitName


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
