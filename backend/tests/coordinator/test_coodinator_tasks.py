import pytest

from quicklook.coordinator.quicklookjob.job_pipeline import make_generate_tasks
from quicklook.types import GeneratorPod, Visit

pytestmark = pytest.mark.focus


def test_make_generator_tasks():
    generators = [
        GeneratorPod(host='localhost', port=8000),
        GeneratorPod(host='localhost', port=8001),
    ]

    tasks = make_generate_tasks(
        visit=Visit.from_id('raw:broccoli'),
        generators=generators,
    )

    assert tasks[0].generator == generators[0]
    assert tasks[0].visit == Visit.from_id('raw:broccoli')
