from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass

import numpy
import requests

from quicklook.comm.generator import self_generator_id
from quicklook.comm.types import GeneratorInfo
from quicklook.generator.job import Job
from quicklook.generator.jobstorage import JobStorage
from quicklook.tileinfo import TileInfo
from quicklook.types import TilePos
from quicklook.utils import multiprocessing_coverage_compatible, zstd
from quicklook.utils.numpyutils import ndarray2npybytes, npybytes2ndarray


def merge_single_fits_tiles(job: Job):
    # 全てのタイルを走査しタイルについて
    # そのタイルのprimary generatorが自身だった場合、そのタイルをマージ対象とする。
    # マージ対象のタイルは他のgeneratorに問い合わせて取得する
    # マージ対象でないタイルは他のgeneratorで処理される
    process_tiles_args = [*iter_process_tiles_args(job)]
    with multiprocessing_coverage_compatible.Pool() as pool:
        for done, _ in enumerate(
            pool.imap_unordered(
                _process_tile,
                process_tiles_args,
                chunksize=32,
            )
        ):
            pass
            # print(done)


def iter_process_tiles_args(job: Job):
    # プライマリジェネレータが自分自身であるタイルをiterateする
    storage = JobStorage(job)
    dist_config = storage.ccd_distribution_config.load()
    valid_ccd_names = set(dist_config.ccd_generator_map.keys())
    for pos in storage.single_fits_tile.iter_tiles():
        ccd_names = [ccd_name for ccd_name in TileInfo.from_pos(pos).ccd_names if ccd_name in valid_ccd_names]
        if len(ccd_names) == 0:  # pragma: no cover
            continue
        if dist_config.ccd_generator_map[ccd_names[0]] == self_generator_id():
            yield ProcessTileArgs(
                storage=storage,
                pos=pos,
                ccd_names=ccd_names,
            )


@dataclass
class ProcessTileArgs:
    storage: JobStorage
    pos: TilePos
    ccd_names: list[str]


def _process_tile(args: ProcessTileArgs):
    storage = args.storage
    dist_config = storage.ccd_distribution_config.load()  # これはキャッシュが使われるはず

    internal_ccd_names: list[str] = []
    external_generators: set[GeneratorInfo] = set()

    for ccd_name in args.ccd_names:
        generator_id = dist_config.ccd_generator_map[ccd_name]
        if generator_id == self_generator_id():
            internal_ccd_names.append(ccd_name)
        else:
            external_generators.add(dist_config.generators[generator_id])

    arr = storage.single_fits_tile.load_local_merged(pos=args.pos, ccd_names=internal_ccd_names)
    if len(external_generators) > 0:
        for _arr in gather_external_tile_data(storage.job_id, args.pos, external_generators):
            arr += _arr
    storage.merged_fits_tile.save_compressed_data(
        pos=args.pos,
        compressed_data=zstd.compress(ndarray2npybytes(arr)),
    )


def gather_external_tile_data(
    job_id: str,
    pos: TilePos,
    external_generators: set[GeneratorInfo],
):
    with ThreadPoolExecutor(len(external_generators)) as executor:
        futures = {executor.submit(get_npy, g, job_id, pos): g for g in external_generators}
        for future in as_completed(futures):
            yield future.result()


def get_npy(generator: GeneratorInfo, job_id: str, pos: TilePos) -> numpy.ndarray | None:
    # OPTIMIZE: 接続を使い回す仕組みを考える
    response = requests.get(f'{generator.url}/jobs/{job_id}/tiles/{pos.level}/{pos.i}/{pos.j}')
    response.raise_for_status()
    return npybytes2ndarray(response.content)
