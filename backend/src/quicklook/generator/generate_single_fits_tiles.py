import contextlib
import tempfile
from pathlib import Path
from typing import Callable

from quicklook.config import config
from quicklook.datasource import get_datasource
from quicklook.generator.iteratetiles import iterate_tiles
from quicklook.generator.jobstorage import JobStorage
from quicklook.generator.preprocess_ccd import PreProcessedCcd, preprocess_ccd
from quicklook.types import CcdId, Progress, Tile
from quicklook.utils.timer import Timer

from .job import Job

ds = get_datasource()


def generate_single_fits_tiles(
    job: Job,
    ccd_id: CcdId,
    on_progress: Callable[[Progress], None] = lambda progress: None,
):
    on_progress(progress := Progress(total=3))

    storage = JobStorage(job)

    data_bytes = ds.get_data(ccd_id)
    on_progress(progress.update())

    try:
        with _bytes_to_file(data_bytes) as path:

            ppccd = preprocess_ccd(ccd_id, path)
            on_progress(progress.update())

            generate_tiles(ppccd, storage=storage)
            on_progress(progress.update())

        storage.fits_header.save(ccd_id, ppccd.headers)
    finally:
        Timer(600, storage.clear_all).start()


def generate_tiles(
    ppccd: PreProcessedCcd,
    *,
    storage: JobStorage,
):
    def cb(tile: Tile, progress: Progress):
        storage.single_fits_tile.save(ppccd.ccd_id.ccd_name, tile)

    iterate_tiles(ppccd, cb)


@contextlib.contextmanager
def _bytes_to_file(data: bytes, dir=config.fitsio_tmpdir):
    dir.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=dir) as f:
        f.write(data)
        f.flush()
        yield Path(f.name)
