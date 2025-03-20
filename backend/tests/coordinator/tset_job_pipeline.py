import pytest

from quicklook.coordinator.quicklookjob.job import QuicklookJob, QuicklookJobPhase
from quicklook.coordinator.quicklookjob.job_generate import _make_generate_tasks
from quicklook.types import GeneratorPod, Visit

pytestmark = pytest.mark.focus


def test_make_generator_tasks():
    generators = [
        GeneratorPod(host='localhost', port=8000),
        GeneratorPod(host='localhost', port=8001),
    ]

    job = QuicklookJob(
        visit=Visit.from_id('raw:broccoli'),
        phase=QuicklookJobPhase.QUEUED,
    )

    tasks, ccd_generator_map = _make_generate_tasks(
        job,
        generators=generators,
    )

    assert tasks[0].generator == generators[0]
    assert tasks[0].visit == Visit.from_id('raw:broccoli')
