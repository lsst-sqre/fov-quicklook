import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from logging import getLogger
from typing import Callable

import requests

from quicklook import storage
from quicklook.config import config
from quicklook.coordinator.quicklookjob.tasks import TransferTask
from quicklook.generator.generatorstorage import mergedtile_storage
from quicklook.select_primary_generator import NoOverlappingGenerators, select_primary_generator
from quicklook.types import PackedTileId, Progress, TileId, TransferProgress, TransferTaskResponse
from quicklook.utils import throttle
from quicklook.utils.timeit import timeit

logger = getLogger(f'uvicorn.{__name__}')


def run_transfer(task: TransferTask, send: Callable[[TransferTaskResponse], None]) -> None:
    @throttle.throttle(0.1)
    def on_update(progress: TransferProgress):
        send(progress)


    def iter_tiles():
        distinct_tiles: set[PackedTileId] = set()
        for level, i, j in mergedtile_storage.iter_tiles(task.visit):
            tile_id = PackedTileId.from_unpacked(level, i, j)
            if tile_id in distinct_tiles:
                continue
            distinct_tiles.add(tile_id)

        yield from distinct_tiles

    with timeit(f'transfer enumerate {task.visit.id}'):
        args_list = list(iter_tiles())
        total = len(args_list)

    on_update(TransferProgress(transfer=Progress(count=0, total=total)))

    with timeit(f'transfer {task.visit.id}'):
        with ThreadPoolExecutor(2) as executor:
            futures = [executor.submit(transfer_packed_tile, task, args) for args in args_list]
            for done, _ in enumerate(as_completed(futures)):
                _.result()
                progress = TransferProgress(transfer=Progress(count=done + 1, total=total))
                on_update(progress)
    throttle.flush(on_update)


def transfer_packed_tile(task: TransferTask, packed_id: PackedTileId) -> None:
    with timeit(f'transfer {task.visit.id} {packed_id}'):
        level = packed_id.level

        def get_zstd(tile_id: TileId) -> bytes | None:
            try:
                generator, _ = select_primary_generator(task.ccd_generator_map, tile_id)
            except NoOverlappingGenerators:
                return None

            if generator == task.generator:
                try:
                    return mergedtile_storage.get_compressed_tile_data(task.visit, tile_id.level, tile_id.i, tile_id.j)
                except FileNotFoundError:
                    return None

            try:
                response = requests.get(f'http://{generator.name}/quicklooks/{task.visit.id}/merged-tiles/{level}/{tile_id.i}/{tile_id.j}', timeout=30)
                response.raise_for_status()
                return response.content
            except requests.HTTPError as e:
                if e.response.status_code == 404:
                    return None
                traceback.print_exc()
                return None
            except Exception:  # pragma: no cover
                traceback.print_exc()
                return None

        with ThreadPoolExecutor((1 << config.tile_pack) ** 2) as executor:
            zstds = executor.map(
                get_zstd,
                packed_id.unpackeds(),
            )
            storage.put_quicklook_packed_tile_array(task.visit, packed_id, [*zstds])
