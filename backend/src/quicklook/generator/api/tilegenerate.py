import contextlib
import json
import logging
import tempfile
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Generator

from quicklook.config import config
from quicklook.coordinator.quicklookjob.tasks import GenerateTask
from quicklook.datasource import get_datasource
from quicklook.generator.iteratetiles import iterate_tiles
from quicklook.generator.preprocess_ccd import preprocess_ccd
from quicklook.generator.progress import GenerateProgress, GeneratorProgressReporter
from quicklook.generator.generatorstorage import tmptile_storage
from quicklook.types import CcdId, CcdMeta, GenerateTaskResponse, PreProcessedCcd, Progress, Tile, Visit
from quicklook.utils import multiprocessing_coverage_compatible as mp
from quicklook.utils import throttle
from quicklook.utils.dynamicsemaphore import DynamicSemaphore
from quicklook.utils.timeit import timeit

logger = logging.getLogger(f'uvicorn.{__name__}')


def run_generate(task: GenerateTask, send: Callable[[GenerateTaskResponse], None]):
    @throttle.throttle(0.1)
    def on_update(progress: GenerateProgress):
        send(progress)

    with iterate_downloaded_ccds(task.visit, task.ccd_names) as files:
        with timeit('generator'):
            with mp.Pool(config.tile_ccd_processing_parallel) as pool:
                with GeneratorProgressReporter(task, on_update=on_update) as progress:

                    def args():
                        for ccd_id, file in files:
                            progress.download_done()
                            yield ProcessCcdArgs(ccd_id, file, progress.updator)

                    for result in pool.imap_unordered(process_ccd, args()):
                        send(result)

    throttle.flush(on_update)


@dataclass
class ProcessCcdArgs:
    ccd_id: CcdId
    path: Path
    progress_updator: GeneratorProgressReporter.InterProcessUpdator


def process_ccd(args: ProcessCcdArgs) -> CcdMeta:
    def update_maketile_progress(progress: Progress):
        if (progress.count == progress.total) or (progress.count % 32 == 0):
            args.progress_updator.update_maketile_progress(args.ccd_id.ccd_name, progress)

    with timeit(f'process-{args.ccd_id.name}'):
        try:
            try:
                ppccd = preprocess_ccd(args.ccd_id, args.path)
                args.progress_updator.preprocess_done()
            finally:
                args.path.unlink()

            save_headers(ppccd)

            make_tiles(
                ppccd,
                update_progress=update_maketile_progress,
            )
        except Exception:
            # 明示的にエラーを書き出さないとエラーログがどこかへ消えてしまう
            logger.exception(f'Failed to process {args.ccd_id.name}')
            raise

    return CcdMeta(
        ccd_id=args.ccd_id,
        image_stat=ppccd.stat,
        amps=ppccd.amps,
        bbox=ppccd.bbox,
    )


def make_tiles(
    ppccd: PreProcessedCcd,
    *,
    update_progress: Callable[[Progress], None],
):
    def cb(tile: Tile, progress: Progress):
        tmptile_storage.put_tile(ppccd.ccd_id, tile)
        update_progress(progress)

    iterate_tiles(ppccd, cb)


@contextlib.contextmanager
def iterate_downloaded_ccds(
    visit: Visit,
    ccd_names: list[str],
    parallel: int = 2,
    update_progress: Callable[[Progress], None] = Progress.noop_progress,
):
    sem = DynamicSemaphore(1)
    ds = get_datasource()

    def download(visit: Visit, ccd_name: str):
        with sem:
            with timeit(f'download-{visit.name}/{ccd_name}'):
                filecontents = ds.get_data(CcdId(visit, ccd_name))
                filename = Path(f'{tmpdir}/{ccd_name}.fits')
                filename.parent.mkdir(parents=True, exist_ok=True)
                Path(filename).write_bytes(filecontents)
                if sem.max_count < parallel:
                    sem.set_max_count(parallel)
                return CcdId(visit, ccd_name), filename

    Path(config.fitsio_tmpdir).mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=config.fitsio_tmpdir) as tmpdir:

        def g():
            with ThreadPoolExecutor(parallel) as executor:
                fs = [executor.submit(download, visit, ccd_name) for ccd_name in ccd_names]
                for i, f in enumerate(as_completed(fs)):
                    update_progress(Progress(i + 1, len(ccd_names)))
                    try:
                        yield f.result()
                    except Exception as e:  # pragma: no cover
                        traceback.print_exc()

        yield g()


def save_headers(ppccd: PreProcessedCcd):
    outfile = Path(f'{config.fits_header_tmpdir}/{ppccd.ccd_id.name}.json')
    outfile.parent.mkdir(parents=True, exist_ok=True)
    with outfile.open('w') as f:
        json.dump(ppccd.headers, f)
