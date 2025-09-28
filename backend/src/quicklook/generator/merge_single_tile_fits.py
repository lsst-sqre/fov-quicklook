from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import ExitStack, contextmanager
from dataclasses import dataclass
import dis
import threading
from typing import Callable

import numpy
import requests

from quicklook.comm.coordinator import get_available_generators
from quicklook.comm.generator import self_generator_id
from quicklook.comm.types import GeneratorInfo
from quicklook.generator.generator_assignment import GeneratorAssignment, NoGeneratorFoundError
from quicklook.job.job import Job
from quicklook.types import CcdName, Progress, TilePos
from quicklook.utils import multiprocessing_coverage_compatible, zstd
from quicklook.utils.numpyutils import ndarray2npybytes, npybytes2ndarray
from quicklook.utils.stacklib import Stack, pool_args, thread_local_context


def merge_single_fits_tiles(job: Job):
    # 全てのタイルを走査しタイルについて
    # そのタイルのprimary generatorが自身だった場合、そのタイルをマージ対象とする。
    # マージ対象のタイルは他のgeneratorに問い合わせて取得する
    # マージ対象でないタイルは他のgeneratorで処理される
    process_tiles_args = [_ProcessTileArgs(job=job, pos=pos) for pos in _iter_primary_pos(job)]
    dist_config = job.local_storage.ccd_distribution_config.load()
    n_generators = len(dist_config.generators)
    yield (p := Progress(len(process_tiles_args)))
    with multiprocessing_coverage_compatible.Pool(**pool_args(enable_pool_context, n_generators)) as pool:
        for _ in pool.imap_unordered(
            _process_tile,
            process_tiles_args,
            chunksize=64,
        ):
            for _ in p.update_and_yield_every(64):
                yield p
    yield p.full()


def _iter_primary_pos(job: Job):
    # プライマリジェネレータが自分自身であるTilePosをiterateする
    storage = job.local_storage
    for pos in storage.single_fits_tile.iter_tiles():
        try:
            ga = GeneratorAssignment(job, pos)
            primary_generator_id = ga.primary_generator_id()
        except NoGeneratorFoundError:  # pragma: no cover
            continue
        if primary_generator_id == self_generator_id():
            yield pos


@dataclass
class _ProcessTileArgs:
    job: Job
    pos: TilePos


def _process_tile(args: _ProcessTileArgs):
    storage = args.job.local_storage
    dist_config = storage.ccd_distribution_config.load()
    ga = GeneratorAssignment(args.job, args.pos)

    internal_ccd_names: list[CcdName] = []
    external_generators: set[GeneratorInfo] = set()

    for ccd_name in ga.ccd_names:
        generator_id = dist_config.ccd_generator_map[ccd_name]
        if generator_id == self_generator_id():
            internal_ccd_names.append(ccd_name)
        else:
            external_generators.add(dist_config.generators[generator_id])

    arr = storage.single_fits_tile.load_local_merged(pos=args.pos, ccd_names=internal_ccd_names)
    if len(external_generators) > 0:
        for _arr in _gather_external_tile_data(storage.job.id, args.pos, external_generators):
            arr += _arr
    storage.merged_fits_tile.save_compressed_data(
        pos=args.pos,
        compressed_data=zstd.compress(ndarray2npybytes(arr)),
    )


def _gather_external_tile_data(
    job_id: str,
    pos: TilePos,
    external_generators: set[GeneratorInfo],
):
    executor = process_context().thread_pool_executor
    futures = (executor.submit(_get_npy, g, job_id, pos) for g in external_generators)
    for fut in as_completed(futures):
        yield fut.result()


def _get_npy(generator: GeneratorInfo, job_id: str, pos: TilePos) -> numpy.ndarray | None:
    # OPTIMIZE: 接続を使い回す仕組みを考える
    session = process_context().thread_local_requests_session()
    response = session.get(f'{generator.url}/jobs/{job_id}/tiles/{pos.level}/{pos.i}/{pos.j}')
    response.raise_for_status()
    return npybytes2ndarray(response.content)


@dataclass
class ProcessContext:
    thread_pool_executor: ThreadPoolExecutor
    thread_local_requests_session: Callable[[], requests.Session]


@contextmanager
def enable_pool_context(n_threads:int):
    with ThreadPoolExecutor(max_workers=n_threads) as executor:
        with thread_local_context(requests.Session) as session:
            ctx = ProcessContext(
                thread_pool_executor=executor,
                thread_local_requests_session=session,
            )
            with process_context.push(ctx):
                yield


process_context = Stack[ProcessContext]()
