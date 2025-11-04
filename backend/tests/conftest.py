import shutil
from quicklook.config import config
import pytest


@pytest.fixture(scope='session', autouse=True)
def clear_temp_files():
    config.job_local_dir.mkdir(parents=True, exist_ok=True)
    yield
    print('Cleaning up temporary files...')
    shutil.rmtree(config.job_local_dir, ignore_errors=True)


@pytest.fixture(autouse=True)
def enable_faulthandler():
    # Enable faulthandler for easier debugging
    import faulthandler, signal, sys

    faulthandler.enable(sys.stderr, all_threads=True)
    faulthandler.register(signal.SIGUSR1, file=sys.stderr, all_threads=True)
