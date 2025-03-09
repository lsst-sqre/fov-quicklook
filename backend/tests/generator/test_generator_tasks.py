import multiprocessing
from pathlib import Path
import tempfile

import pytest

from quicklook.coordinator.quicklookjob.tasks import GeneratorPod, GeneratorTask
from quicklook.generator import progress, tasks
from quicklook.generator.progress import GeneratorProgressReporter, tqdm_progres_bar
from quicklook.types import CcdId, GeneratorProgress, Visit


# @pytest.mark.focus
async def test_phase_raw():
    ccd_names = [*''' R22_S00  R22_S01 '''.split()]
    # ccd_names = [
    #     *'''
    #     R22_S00  R22_S01  R22_S02  R22_S10  R22_S11  R22_S12  R22_S20  R22_S21  R22_S22
    #     R23_S00  R23_S01  R23_S02  R23_S10  R23_S11  R23_S12  R23_S20  R23_S21  R23_S22'''.split()
    # ]

    visit = Visit.from_id('raw:broccoli')
    task = GeneratorTask(
        visit=visit,
        ccd_names=ccd_names,
        generator=GeneratorPod(host='localhost', port=8000),
        ccd_generator_map={},
    )

    with tqdm_progres_bar(task) as on_update:
        tasks.run_generator(task, on_update=on_update)


# @pytest.mark.focus
async def test_phase_calexp():
    ccd_names = [*''' R21_S00 R21_S01  '''.split()]
    # ccd_names = [
    #     *'''
    #     R22_S00  R22_S01  R22_S02  R22_S10  R22_S11  R22_S12  R22_S20  R22_S21  R22_S22
    #     R23_S00  R23_S01  R23_S02  R23_S10  R23_S11  R23_S12  R23_S20  R23_S21  R23_S22'''.split()
    # ]

    visit = Visit.from_id('calexp:192350')
    task = GeneratorTask(
        visit=visit,
        ccd_names=ccd_names,
        generator=GeneratorPod(host='localhost', port=8000),
        ccd_generator_map={},
    )

    with tqdm_progres_bar(task) as on_update:
        tasks.run_generator(task, on_update=on_update)


# @pytest.mark.focus
def test_progress():
    import pickle

    task = GeneratorTask(
        generator=GeneratorPod(host='localhost', port=8000),
        ccd_names=['R23_S00'],
        visit=Visit.from_id('raw:broccoli'),
        ccd_generator_map={},
    )

    progress = tasks.GeneratorProgressReporter(task)
    pickle.dumps(progress)


def test_processccd(broccoli_fits_and_ccd_id: tuple[Path, str]):
    path, ccd = broccoli_fits_and_ccd_id

    def on_update(progress: GeneratorProgress):
        print(progress)

    with GeneratorProgressReporter(
        task=GeneratorTask(
            visit=Visit.from_id('raw:broccoli'),
            ccd_names=[ccd],
            generator=GeneratorPod(host='localhost', port=8000),
            ccd_generator_map={},
        ),
        on_update=on_update,
    ) as progress_reporter:
        # to prevent the fixture from being deleted
        with tempfile.NamedTemporaryFile() as tmp:
            tmp.write(path.read_bytes())
            tmp.flush()
            args = tasks.ProcessCcdArgs(
                ccd_id=CcdId(visit=Visit.from_id('raw:broccoli'), ccd_name=ccd),
                path=Path(tmp.name),
                progress_updator=progress_reporter.updator,
            )
            tasks.process_ccd(args)
