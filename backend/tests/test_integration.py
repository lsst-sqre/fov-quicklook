import pytest

from quicklook.dev.run_uvicorn import run_uvicorn_app


@pytest.fixture(scope='module')
def coordinator_and_generator():
    with run_uvicorn_app(
        'quicklook.coordinator.app:app',
        port=9501,
        log_prefix='[coordinator] ',
        healthz='/comm/healthz',
    ) as wait_for_coordinator:
        wait_for_coordinator()
        with run_uvicorn_app(
            'quicklook.coordinator.app:app',
            port=9502,
            log_prefix='[generator] ',
            healthz='/comm/healthz',
        ) as wait_for_generator:
            wait_for_generator()
            pass


def test_rpc_integrated():
    pass
