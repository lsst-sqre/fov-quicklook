from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Iterable

import requests

from quicklook.comm.generator import self_generator_id
from quicklook.config import config
from quicklook.generator.generator_assignment import GeneratorAssignment, NoGeneratorFoundError
from quicklook.job.job import Job
from quicklook.tileinfo import ccds_by_name
from quicklook.types import PackedTilePos, Progress, ReturnValue, TilePos
from quicklook.utils.geom import BBox


def transfer_tiles(job: Job):
    # 4x4のタイルをまとめてオブジェクトストレージに転送する。
    # (1つ1つだとオーバーヘッドが大きすぎるので。)
    packed_pos_list = [*_iter_primary_packed_tile_pos(job)]
    yield (p := Progress(len(packed_pos_list)))

    uploaded_size = 0

    with ThreadPoolExecutor(config.transfer_tile_parallel) as executor:
        futs = [executor.submit(_process_packed_tile, job, pos) for pos in packed_pos_list]
        for fut in as_completed(futs):
            uploaded_size += fut.result()
            for _ in p.update_and_yield_every(16):
                yield p

    yield p.full()
    yield ReturnValue(uploaded_size)


def _process_packed_tile(job: Job, packed_pos: PackedTilePos):
    # とあるpacked_tileに対してそれに含まれるtileを集めて
    # オブジェクトストレージにアップロードする

    def get_merged_tile(pos: TilePos) -> bytes | None:
        ga = GeneratorAssignment(job, pos)
        try:
            primary_generator_id = ga.primary_generator_id()
        except NoGeneratorFoundError:
            return

        if primary_generator_id == self_generator_id():
            return job.local_storage.merged_fits_tile.load_compressed_data(pos)
        else:
            base_url = ga.dist_config.generators[primary_generator_id].url
            response = requests.get(f'{base_url}/jobs/{job.id}/merged-tiles/{pos.level}/{pos.i}/{pos.j}', timeout=10)
            match response.status_code:
                case 200:
                    return response.content
                case 404:  # pragma: no cover
                    # ここには来ないはずだが
                    return
                case _:  # pragma: no cover
                    response.raise_for_status()

    with ThreadPoolExecutor((1 << config.tile_pack) ** 2) as executor:
        merged_tiles = executor.map(
            get_merged_tile,
            packed_pos.unpackeds(),
        )
        uploaded_size = job.object_storage.put_packed_tile_array(packed_pos, [*merged_tiles])
        return uploaded_size


def _iter_primary_packed_tile_pos(job: Job) -> Iterable[PackedTilePos]:
    dist_config = job.local_storage.ccd_distribution_config.load()

    packed_pos_list: set[PackedTilePos] = set()
    for ccd_name in dist_config.ccd_generator_map.keys():
        bbox = ccds_by_name()[ccd_name].bbox
        packed_pos_list |= set(map(PackedTilePos.from_unpacked, _iterate_pos(bbox)))

    generator_ids = [*dist_config.generators.keys()]
    for packed_pos in packed_pos_list:
        if generator_ids[packed_pos.safe_hash() % len(generator_ids)] == self_generator_id():
            yield packed_pos


def _iterate_pos(bbox: BBox):
    tile_size = config.tile_size
    max_level = config.tile_max_level
    h = bbox.maxy - bbox.miny
    w = bbox.maxx - bbox.minx
    y1 = int(bbox.miny)
    x1 = int(bbox.minx)
    y2 = int(y1 + h)
    x2 = int(x1 + w)
    for level in range(max_level + 1):  # pragma: no branch
        tile_yi1 = y1 // tile_size
        tile_yi2 = (y2 - 1) // tile_size + 1
        tile_xi1 = x1 // tile_size
        tile_xi2 = (x2 - 1) // tile_size + 1
        for tile_yi in range(tile_yi1, tile_yi2):
            for tile_xi in range(tile_xi1, tile_xi2):
                yield TilePos(level=level, i=tile_yi, j=tile_xi)
        if level >= max_level:
            break
        if y1 % 2 != 0:
            y1 -= 1
        if y2 % 2 != 0:
            y2 += 1
        if x1 % 2 != 0:
            x1 -= 1
        if x2 % 2 != 0:
            x2 += 1
        y1 //= 2
        x1 //= 2
        y2 //= 2
        x2 //= 2
