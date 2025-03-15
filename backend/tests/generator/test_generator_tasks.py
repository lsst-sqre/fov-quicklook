import multiprocessing
from pathlib import Path
import tempfile

import pytest

from quicklook.coordinator.quicklookjob.tasks import GeneratorPod, GenerateTask
from quicklook.generator import progress, tilegenerate
from quicklook.generator.progress import GeneratorProgressReporter, tqdm_progres_bar
from quicklook.types import CcdId, GenerateProgress, Visit


# @pytest.mark.focus
async def test_phase_raw():
    ccd_names = [*''' R22_S00  R22_S01 '''.split()]
    # ccd_names = [
    #     *'''
    #     R22_S00  R22_S01  R22_S02  R22_S10  R22_S11  R22_S12  R22_S20  R22_S21  R22_S22
    #     R23_S00  R23_S01  R23_S02  R23_S10  R23_S11  R23_S12  R23_S20  R23_S21  R23_S22'''.split()
    # ]

    visit = Visit.from_id('raw:broccoli')
    task = GenerateTask(
        visit=visit,
        ccd_names=ccd_names,
        generator=GeneratorPod(host='localhost', port=8000),
    )

    with tqdm_progres_bar() as on_update:
        tilegenerate.run_generate(task, on_update)


# @pytest.mark.focus
async def test_phase_calexp():
    ccd_names = [*''' R21_S00 R21_S01  '''.split()]
    # ccd_names = [
    #     *'''
    #     R22_S00  R22_S01  R22_S02  R22_S10  R22_S11  R22_S12  R22_S20  R22_S21  R22_S22
    #     R23_S00  R23_S01  R23_S02  R23_S10  R23_S11  R23_S12  R23_S20  R23_S21  R23_S22'''.split()
    # ]

    visit = Visit.from_id('calexp:192350')
    task = GenerateTask(
        visit=visit,
        ccd_names=ccd_names,
        generator=GeneratorPod(host='localhost', port=8000),
    )

    with tqdm_progres_bar() as on_update:
        tilegenerate.run_generate(task, on_update)


# @pytest.mark.focus
def test_progress():
    import pickle

    task = GenerateTask(
        generator=GeneratorPod(host='localhost', port=8000),
        ccd_names=['R23_S00'],
        visit=Visit.from_id('raw:broccoli'),
    )

    progress = tilegenerate.GeneratorProgressReporter(task)
    pickle.dumps(progress)


def test_processccd(broccoli_fits_and_ccd_id: tuple[Path, str]):
    path, ccd = broccoli_fits_and_ccd_id

    def on_update(progress: GenerateProgress):
        print(progress)

    with GeneratorProgressReporter(
        task=GenerateTask(
            visit=Visit.from_id('raw:broccoli'),
            ccd_names=[ccd],
            generator=GeneratorPod(host='localhost', port=8000),
        ),
        on_update=on_update,
    ) as progress_reporter:
        # to prevent the fixture from being deleted
        with tempfile.NamedTemporaryFile() as tmp:
            tmp.write(path.read_bytes())
            tmp.flush()
            args = tilegenerate.ProcessCcdArgs(
                ccd_id=CcdId(visit=Visit.from_id('raw:broccoli'), ccd_name=ccd),
                path=Path(tmp.name),
                progress_updator=progress_reporter.updator,
            )
            tilegenerate.process_ccd(args)
