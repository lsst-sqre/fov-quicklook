import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from logging import getLogger
from typing import Callable, Generator

import numpy
import requests

from quicklook import storage
from quicklook.config import config
from quicklook.coordinator.quicklookjob.tasks import TransferTask
from quicklook.generator.tmptile import tmptile
from quicklook.tileinfo import TileInfo
from quicklook.types import GeneratorPod, Progress, Tile, TransferProgress, TransferTaskResponse, Visit
from quicklook.utils import multiprocessing_coverage_compatible, throttle
from quicklook.utils.numpyutils import npybytes2ndarray
from quicklook.utils.timeit import timeit

logger = getLogger(f'uviorn.{__name__}')


@dataclass(frozen=True)
class TileId:
    level: int
    i: int
    j: int


@dataclass
class Context:
    visit: Visit
    tile_id: TileId
    generators: list[GeneratorPod]


def run_transfer(task: TransferTask, send: Callable[[TransferTaskResponse], None]) -> None:
    def iter_tiles():
        for level, i, j in tmptile.iter_tiles(task.visit):
            tile_id = TileId(level, i, j)
            primary, all_generators = get_generators_info(task, tile_id)
            if primary == task.generator:
                non_primary_generators = [g for g in all_generators if g != primary]
                yield Context(
                    visit=task.visit,
                    tile_id=tile_id,
                    generators=non_primary_generators,
                )

    @throttle.throttle(0.1)
    def on_update(progress: TransferProgress):
        send(progress)

    total = count_total_tiles(task)

    with multiprocessing_coverage_compatible.Pool(config.tile_transfer_parallel) as pool:
        done = 0
        for _ in pool.imap_unordered(process_tile, iter_tiles(), chunksize=32):
            done += 1
            progress = TransferProgress(
                transfer=Progress(
                    count=done,
                    total=total,
                ),
            )
            on_update(progress)
    throttle.flush(on_update)


def count_total_tiles(task: TransferTask) -> int:
    count = 0
    for level, i, j in tmptile.iter_tiles(task.visit):
        tile_id = TileId(level, i, j)
        primary, all_generators = get_generators_info(task, tile_id)
        if primary == task.generator:
            count += 1
    return count


def process_tile(ctx: Context) -> None:
    tile_id = ctx.tile_id
    visit = ctx.visit
    npy = tmptile.get_tile_npy(visit, tile_id.level, tile_id.i, tile_id.j)
    if len(ctx.generators) > 0:
        for tile in gather_tiles(ctx.generators, visit, tile_id.level, tile_id.i, tile_id.j):
            npy += tile
    storage.put_quicklook_tile(Tile(visit=visit, level=tile_id.level, i=tile_id.i, j=tile_id.j, data=npy))


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


def get_generators_info(task: TransferTask, tile_id: TileId) -> tuple[GeneratorPod, list[GeneratorPod]]:
    """
    タイルに関わる generator の情報を返す

    Returns:
        tuple: (primary generator, すべての関連 generators のリスト)
    """
    ccd_names = TileInfo.of(tile_id.level, tile_id.i, tile_id.j).ccd_names
    generators = sorted(set(g for g in (task.ccd_generator_map.get(ccd_name) for ccd_name in ccd_names) if g), key=lambda g: (g.name, g.port))
    # generatorsがこのtileを生成するために必要なgeneratorの集合
    # この中からgeneratorを１つだけ選ぶ
    # どれを選んでも良いが、負荷分散のために tile_id を使ってランダムに選ぶ
    primary = generators[hash(tile_id) % len(generators)]
    return primary, generators
