import contextlib
import tempfile
from pathlib import Path

from quicklook.config import config
from quicklook.datasource import get_datasource
from quicklook.generator.iteratetiles import iterate_tiles
from quicklook.generator.job.localstorage import JobLocalStorage
from quicklook.generator.preprocess_ccd import PreProcessedCcd, preprocess_ccd
from quicklook.job import Job
from quicklook.types import CcdId, Progress, Tile

ds = get_datasource()


def generate_single_fits_tiles(job: Job, ccd_id: CcdId):
    local_storage = JobLocalStorage(job)
    data_bytes = ds.get_data(ccd_id)
    with _bytes_to_file(data_bytes) as path:
        ppccd = preprocess_ccd(ccd_id, path)
        generate_tiles(ppccd, local_storage=local_storage)
    local_storage.save_fits_header(ccd_id, ppccd.headers)


def generate_tiles(
    ppccd: PreProcessedCcd,
    *,
    local_storage: JobLocalStorage,
):
    def cb(tile: Tile, progress: Progress):
        local_storage.save_single_fits_tile(ppccd.ccd_id, tile)

    iterate_tiles(ppccd, cb)


@contextlib.contextmanager
def _bytes_to_file(data: bytes, dir=config.fitsio_tmpdir):
    dir.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=dir) as f:
        f.write(data)
        f.flush()
        yield Path(f.name)
