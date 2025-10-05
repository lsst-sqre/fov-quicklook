import pytest

from quicklook.dev.run_uvicorn import run_uvicorn_app


@pytest.fixture(scope='module')
def coordinator_and_generator():
    with run_uvicorn_app(
        'quicklook.coordinator.api.app:app',
        port=9501,
        log_prefix='[coordinator] ',
        healthz='/comm/healthz',
    ) as coordinator_runner:
        coordinator_runner.wait_for_ready()
        with run_uvicorn_app(
            'quicklook.coordinator.api.app:app',
            port=9502,
            log_prefix='[generator] ',
            healthz='/comm/healthz',
        ) as generator_runner:
            generator_runner.wait_for_ready()
            pass


def test_rpc_integrated():
    pass
