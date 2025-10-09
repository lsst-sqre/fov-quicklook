import contextlib
import multiprocessing
import tempfile
from dataclasses import dataclass
from pathlib import Path

from quicklook.config import config
from quicklook.datasource import get_datasource
from quicklook.generator.iteratetiles import iterate_tiles
from quicklook.generator.preprocess_ccd import AmpMetadata, ImageStat, PreProcessedCcd, preprocess_ccd
from quicklook.types import CcdDataRef, CcdName, Progress, ReturnValue, Tile
from quicklook.utils.geom import BBox
from quicklook.utils.timer import Timer

from quicklook.job.job import Job

ds = get_datasource()

def generate_single_fits_tiles(
    job: Job,
    ref: CcdDataRef,
):
    yield (progress := Progress(total=3))

    data_bytes = ds.get_data_sync(ref)
    yield progress.update()

    try:
        with _bytes_to_file(data_bytes) as path:
            ppccd = preprocess_ccd(ref, path)
            yield progress.update()
        
        generate_tiles(ppccd, job)
        yield progress.update()

        job.local_storage.fits_header.save(ref, ppccd.headers)

        yield ReturnValue(
            CcdMetadata(
                ccd_name=ppccd.data_ref.ccd,
                image_stat=ppccd.stat,
                amps=ppccd.amps,
                bbox=ppccd.bbox,
            )
        )
    finally:
        # 遅いgeneratorでこの関数が実行された時
        # coordinatorのcleanupの後にまだこの関数が実行されている可能性がるので
        # ここでもcleanupする。
        #
        # from threading import Timer
        # なぜかPython標準のTimerを使うとgenerator全体が停止してしまう。
        Timer(600, job.local_storage.clear_all).start()


@dataclass
class CcdMetadata:
    ccd_name: CcdName
    image_stat: ImageStat
    amps: list[AmpMetadata]
    bbox: BBox


def generate_tiles(
    ppccd: PreProcessedCcd,
    job: Job,
):
    storage = job.local_storage

    def cb(tile: Tile):
        storage.single_fits_tile.save(ppccd.data_ref.ccd, tile)

    iterate_tiles(ppccd, cb)


@contextlib.contextmanager
def _bytes_to_file(data: bytes, dir=config.fitsio_tmpdir):
    dir.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=dir) as f:
        f.write(data)
        f.flush()
        yield Path(f.name)
