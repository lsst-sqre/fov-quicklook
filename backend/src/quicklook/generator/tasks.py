import contextlib
import logging
import tempfile
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import minio

from quicklook.config import config
from quicklook.coordinator.tasks import GeneratorTask
from quicklook.generator.iteratetiles import iterate_tiles
from quicklook.generator.preprocess_ccd import preprocess_ccd
from quicklook.generator.progress import GeneratorProgress, GeneratorProgressReporter
from quicklook.generator.tilewriter import TileWriter, TileWriterBase
from quicklook.storage import s3_get_visit_ccd_fits
from quicklook.tileinfo import TileInfo
from quicklook.types import CcdId, ImageStat, PreProcessedCcd, ProcessCcdResult, Progress, Tile, Visit
from quicklook.utils import multiprocessing_coverage_compatible as mp
from quicklook.utils.dynamicsemaphore import DynamicSemaphore
from quicklook.utils.timeit import timeit


def run_generator(task: GeneratorTask, on_update: Callable[[GeneratorProgress], None] | None = None) -> list[ProcessCcdResult]:
    with iterate_downloaded_ccds(task.visit, task.ccd_names) as files:
        with timeit('generator'):
            with mp.Pool(config.tile_ccd_processing_parallel) as pool:
                with GeneratorProgressReporter(task, on_update=on_update) as progress:

                    def args():
                        for ccd_id, file in files:
                            progress.download_done()
                            yield ProcessCcdArgs(ccd_id, file, progress.updator)

                    results: list[ProcessCcdResult] = []
                    for result in pool.imap_unordered(process_ccd, args()):
                        results.append(result)
                    return results


@dataclass
class ProcessCcdArgs:
    ccd_id: CcdId
    path: Path
    progress_updator: GeneratorProgressReporter.InterProcessUpdator


def process_ccd(args: ProcessCcdArgs) -> ProcessCcdResult:
    def update_maketile_progress(progress: Progress):
        if (progress.count == progress.total) or (progress.count % 32 == 0):
            args.progress_updator.update_maketile_progress(args.ccd_id.ccd_name, progress)

    with timeit(f'process-{args.ccd_id.name}'):
        ppccd = preprocess_ccd(args.ccd_id, args.path)
        args.progress_updator.preprocess_done()
        args.path.unlink()

        with TileWriter(args.ccd_id) as tile_writer:
            make_tiles(
                ppccd,
                tile_writer=tile_writer,
                update_progress=update_maketile_progress,
            )

    return ProcessCcdResult(
        ccd_id=args.ccd_id,
        image_stat=ppccd.stat,
    )


def make_tiles(
    ppccd: PreProcessedCcd,
    *,
    tile_writer: TileWriterBase,
    update_progress: Callable[[Progress], None],
):
    def cb(tile: Tile, progress: Progress):
        tile_info = TileInfo.of(tile.level, tile.i, tile.j)
        fragment = len(tile_info.ccd_names) >= 2
        tile_writer.put(tile, fragment=fragment)
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

    def download(visit: Visit, ccd_name: str):
        with sem:
            with timeit(f'download-{visit.name}/{ccd_name}'):
                filecontents = s3_get_visit_ccd_fits(visit, ccd_name)
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
                    except minio.error.S3Error as e:  # pragma: no cover
                        logging.warning(e)
                    except Exception as e:  # pragma: no cover
                        traceback.print_exc()

        yield g()
