from os import rmdir
import shutil
from quicklook.config import config
import pytest


@pytest.fixture(scope='session', autouse=True)
def clear_temp_files():
    config.job_local_dir.mkdir(parents=True, exist_ok=True)
    yield
    # shutil.rmtree(config.job_local_dir, ignore_errors=True)
