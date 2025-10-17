import asyncio
import queue
from collections import deque

from quicklook.comm.coordinator import get_available_generators
from quicklook.comm.rpc_worker import rpc_scatter
from quicklook.comm.types import GeneratorId, GeneratorInfo
from quicklook.config import config
from quicklook.generator.generate_single_fits_tiles import (
    CcdMetadata,
    GenerateSingleFitsTilesProgress,
    generate_single_fits_tiles_pipeline,
)
from quicklook.job.job import Job
from quicklook.job.local_storage import CcdDistributionConfig
from quicklook.rpc.client import Rpc
from quicklook.rpc.queue import RpcQueue
from quicklook.types import CcdDataRef, CcdName


async def generate_single_fits_tiles_coordinator(job: Job, ccd_refs: list[CcdDataRef]) -> list[CcdMetadata]:
    """
    FITS データから単一タイルを生成する協調処理。

    各ジェネレータに対して1つのRPC呼び出しを行い、
    queue.Queue を通じて動的にCCDを割り当てる。
    各ジェネレータは設定された数のCCDを同時に処理できる。

    動的割り当ての利点:
      - 高速なジェネレータがより多くのCCDを処理
      - 低速なジェネレータがボトルネックにならない
      - 自動的に最適な負荷分散を実現
    """
    generators = get_available_generators()
    if not generators:
        raise RuntimeError("No generators available")

    generator_list = list(generators.values())
    remaining_ccds = deque(ccd_refs)
    ccd_metadata_dict: dict[CcdName, CcdMetadata] = {}
    ccd_generator_map: dict[CcdName, GeneratorId] = {}
    lock = asyncio.Lock()
    max_concurrent_ccds = config.generator_max_concurrent_ccds_per_job

    async def worker(generator: GeneratorInfo):
        """
        各ジェネレータのワーカー。
        単一のRPC呼び出しでRpcQueue経由で動的にCCDを供給する。
        """
        client_queue: asyncio.Queue[CcdDataRef | None] = asyncio.Queue()

        async with lock:
            initial_batch: list[CcdDataRef] = []
            for _ in range(max_concurrent_ccds):
                if remaining_ccds:
                    ccd_ref = remaining_ccds.popleft()
                    initial_batch.append(ccd_ref)
                    await client_queue.put(ccd_ref)

        if not initial_batch:
            return

        rpc_queue = RpcQueue(client_queue)

        rpc = Rpc(
            f'{generator.ws_url}/rpc',
            _generate_tiles_with_queue,
            job,
            rpc_queue,
        )

        all_sent = False
        async for msg in rpc.iterate():
            match msg:
                case GenerateSingleFitsTilesProgress(progress=progress, ccd_name=ccd_name):
                    async with job.watcher.watch_status():
                        job.status.generate_single_fits_tiles[ccd_name] = progress
                case CcdMetadata(ccd_name=ccd_name):
                    async with lock:
                        ccd_metadata_dict[ccd_name] = msg
                        ccd_generator_map[ccd_name] = generator.id

                    async with lock:
                        if remaining_ccds:
                            next_ccd = remaining_ccds.popleft()
                            await client_queue.put(next_ccd)
                        elif not all_sent:
                            await client_queue.put(None)
                            all_sent = True

    # すべてのジェネレータに対して並行処理
    async with asyncio.TaskGroup() as tg:
        for generator in generator_list:
            tg.create_task(worker(generator))

    if len(ccd_metadata_dict) != len(ccd_refs):
        raise RuntimeError(f"Not all CCDs processed: got {len(ccd_metadata_dict)}/{len(ccd_refs)} metadata")

    dist_config = CcdDistributionConfig(ccd_generator_map, generators)
    async with job.watcher.notify_shared_large_status():
        job.shared_large_status.dist_config = dist_config
        job.shared_large_status.ccd_metadata_list = [*ccd_metadata_dict.values()]

    await rpc_scatter(_save_job_metadata_rpc, job)
    await rpc_scatter(_save_ccd_distribution_config_rpc, job, dist_config)

    return [*ccd_metadata_dict.values()]


def _generate_tiles_with_queue(job: Job, ccd_queue: queue.Queue[CcdDataRef | None]):
    """
    ジェネレータプロセスで実行される RPC 関数。
    queueから動的にCCDを取得して処理する。

    Args:
        job: ジョブオブジェクト
        ccd_queue: CCDを供給するキュー。Noneが送られると終了。

    Yields:
        CcdMetadata: 処理完了したCCDのメタデータ

    Note:
        GeneratorIDはRPC ProcessPoolExecutorのinitializerで設定済み
    """

    def ccd_refs_generator():
        """キューからCCDを取得するジェネレータ"""
        while True:
            ccd_ref = ccd_queue.get()
            if ccd_ref is None:
                break
            yield ccd_ref

    yield from generate_single_fits_tiles_pipeline(job, ccd_refs_generator())


def _save_job_metadata_rpc(job: Job) -> None:
    """ジョブのメタデータをローカルストレージに保存。"""
    job.local_storage.metadata.save()


def _save_ccd_distribution_config_rpc(job: Job, dist_config: CcdDistributionConfig) -> None:
    """CCD とジェネレータの対応関係をローカルストレージに保存。"""
    job.local_storage.ccd_distribution_config.save(dist_config)
