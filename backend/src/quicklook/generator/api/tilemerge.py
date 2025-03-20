import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from logging import getLogger
from typing import Callable, Generator

import numpy
import requests

from quicklook.config import config
from quicklook.coordinator.quicklookjob.tasks import MergeTask
from quicklook.generator.generatorstorage import mergedtile_storage, tmptile_storage
from quicklook.select_primary_generator import select_primary_generator
from quicklook.types import GeneratorPod, MergeProgress, MergeTaskResponse, Progress, TileId, Visit
from quicklook.utils import multiprocessing_coverage_compatible, throttle, zstd
from quicklook.utils.numpyutils import ndarray2npybytes, npybytes2ndarray
from quicklook.utils.timeit import timeit

logger = getLogger(f'uvicorn.{__name__}')


@dataclass
class Args:
    visit: Visit
    tile_id: TileId
    generators: list[GeneratorPod]


def run_merge(task: MergeTask, send: Callable[[MergeTaskResponse], None]) -> None:
    def iter_tiles():
        for level, i, j in tmptile_storage.iter_tiles(task.visit):
            tile_id = TileId(level, i, j)
            primary, all_generators = select_primary_generator(task.ccd_generator_map, tile_id)
            if primary == task.generator:
                non_primary_generators = [g for g in all_generators if g != primary]
                yield Args(
                    visit=task.visit,
                    tile_id=tile_id,
                    generators=non_primary_generators,
                )

    @throttle.throttle(0.1)
    def on_update(progress: MergeProgress):
        send(progress)

    with timeit(f'merge enumerate {task.visit.id}'):
        params_list = list(iter_tiles())
        total = len(params_list)

    on_update(MergeProgress(merge=Progress(count=0, total=total)))

    with timeit(f'merge {task.visit.id}'):
        with multiprocessing_coverage_compatible.Pool(config.tile_merge_parallel) as pool:
            for done, _ in enumerate(pool.imap_unordered(process_tile, params_list)):
                progress = MergeProgress(merge=Progress(count=done + 1, total=total))
                on_update(progress)

    throttle.flush(on_update)


def process_tile(params: Args) -> None:
    tile_id = params.tile_id
    visit = params.visit
    npy = tmptile_storage.get_tile_npy(visit, tile_id.level, tile_id.i, tile_id.j)
    if len(params.generators) > 0:
        for tile in gather_tiles(params.generators, visit, tile_id.level, tile_id.i, tile_id.j):
            npy += tile
    compressed = zstd.compress(ndarray2npybytes(npy))
    mergedtile_storage.put_compressed_tile_data(visit, tile_id.level, tile_id.i, tile_id.j, compressed)


def gather_tiles(
    generators: list[GeneratorPod],
    visit: Visit,
    z: int,
    y: int,
    x: int,
) -> Generator[numpy.ndarray, None, None]:
    """Generator function that yields tile arrays as they become available"""

    def get_npy(generator: GeneratorPod) -> numpy.ndarray | None:
        try:
            response = requests.get(f'http://{generator.name}/quicklooks/{visit.id}/tiles/{z}/{y}/{x}', timeout=30)
            response.raise_for_status()
            return npybytes2ndarray(response.content)
        except Exception:  # pragma: no cover
            traceback.print_exc()
            return None

    with ThreadPoolExecutor(len(generators)) as executor:
        futures = {executor.submit(get_npy, g): g for g in generators}
        for future in as_completed(futures):
            arr = future.result()
            if arr is None:  # pragma: no cover
                continue
            yield arr
