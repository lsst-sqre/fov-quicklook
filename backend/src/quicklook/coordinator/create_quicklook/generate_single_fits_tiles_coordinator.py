import asyncio
import queue
from collections import deque
from typing import cast

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

# Global cache for RPC connections
# Key: GeneratorId
# Value: (RpcQueue, Task)
_rpc_cache: dict[GeneratorId, tuple[RpcQueue, asyncio.Task]] = {}

# Dispatcher for messages from generators
# Key: job_id
# Value: asyncio.Queue[tuple[GeneratorId, GenerateSingleFitsTilesProgress | CcdMetadata]]
_message_dispatcher: dict[str, asyncio.Queue] = {}


async def _rpc_listener(rpc: Rpc, generator_id: GeneratorId):
    """RPCからのメッセージを受信して適切なジョブのキューに振り分ける"""
    try:
        async for msg in rpc.iterate():
            job_id = None
            match msg:
                case GenerateSingleFitsTilesProgress(job_id=jid):
                    job_id = jid
                case CcdMetadata(job_id=jid):
                    job_id = jid
            
            if job_id and job_id in _message_dispatcher:
                await _message_dispatcher[job_id].put((generator_id, msg))
    except Exception:
        # 接続エラーなどはここでハンドリング（再接続ロジックなどが必要ならここ）
        # 現状はキャッシュから削除して終了
        if generator_id in _rpc_cache:
            del _rpc_cache[generator_id]


async def generate_single_fits_tiles_coordinator(job: Job, ccd_refs: list[CcdDataRef]) -> list[CcdMetadata]:
    """
    FITS データから単一タイルを生成する協調処理。

    各ジェネレータに対して永続的なRPC接続を維持し、
    空いているジェネレータに動的にCCDを割り当てる。
    遅いジェネレータがある場合は、他のジェネレータに再割り当て（投機的実行）を行う。
    """
    ccd_refs.sort(key=lambda ref: ref.ccd_name)
    generators = get_available_generators()
    if not generators:
        raise RuntimeError("No generators available")

    generator_list = list(generators.values())
    
    # Register message queue for this job
    msg_queue: asyncio.Queue[tuple[GeneratorId, GenerateSingleFitsTilesProgress | CcdMetadata]] = asyncio.Queue()
    _message_dispatcher[job.id] = msg_queue
    
    try:
        # Ensure RPC connections are established
        queues: dict[GeneratorId, queue.Queue] = {}
        for generator in generator_list:
            if generator.id not in _rpc_cache:
                client_queue: asyncio.Queue[tuple[Job, CcdDataRef] | None] = asyncio.Queue()
                rpc_queue = RpcQueue(client_queue)
                
                rpc = Rpc(
                    f'{generator.ws_url}/rpc',
                    _generate_tiles_with_queue,
                    rpc_queue,
                )
                
                task = asyncio.create_task(_rpc_listener(rpc, generator.id))
                _rpc_cache[generator.id] = (rpc_queue, task)
            
            queues[generator.id] = _rpc_cache[generator.id][0]

        # Dispatch logic
        remaining_ccds = deque(ccd_refs)
        ccd_metadata_dict: dict[CcdName, CcdMetadata] = {}
        ccd_generator_map: dict[CcdName, GeneratorId] = {}
        
        # Track which generator is processing which CCD
        processing_ccds: dict[CcdName, list[GeneratorId]] = {}
        
        # Track load (approximate number of pending tasks for THIS job)
        generator_load: dict[GeneratorId, int] = {g.id: 0 for g in generator_list}
        max_concurrent = config.generator_max_concurrent_ccds_per_job
        
        def dispatch_one(generator_id: GeneratorId, ccd_ref: CcdDataRef):
            queues[generator_id].queue.put_nowait((job, ccd_ref))
            generator_load[generator_id] += 1
            if ccd_ref.ccd_name not in processing_ccds:
                processing_ccds[ccd_ref.ccd_name] = []
            processing_ccds[ccd_ref.ccd_name].append(generator_id)

        def try_dispatch(generator_id: GeneratorId):
            if generator_load[generator_id] >= max_concurrent:
                return

            if remaining_ccds:
                dispatch_one(generator_id, remaining_ccds.popleft())
            else:
                # Speculative dispatch
                pending = [ref for ref in ccd_refs if ref.ccd_name not in ccd_metadata_dict]
                if not pending:
                    return
                
                # Sort pending by number of replicas (ascending)
                pending.sort(key=lambda ref: len(processing_ccds.get(ref.ccd_name, [])))
                
                for ref in pending:
                    current_runners = processing_ccds.get(ref.ccd_name, [])
                    if generator_id not in current_runners:
                        dispatch_one(generator_id, ref)
                        break

        # Initial dispatch: fill all generators
        for generator in generator_list:
            for _ in range(max_concurrent):
                try_dispatch(generator.id)
        
        # Loop until all CCDs are processed
        while len(ccd_metadata_dict) < len(ccd_refs):
            try:
                # Wait for message or timeout to do speculative dispatch
                item = await asyncio.wait_for(msg_queue.get(), timeout=0.5)
                gen_id, msg = item
                
                match msg:
                    case GenerateSingleFitsTilesProgress(progress=progress, ccd_name=ccd_name):
                        async with job.watcher.watch_status():
                            job.status.generate_single_fits_tiles[ccd_name] = progress
                    
                    case CcdMetadata(ccd_name=ccd_name) as metadata:
                        generator_load[gen_id] -= 1
                        if ccd_name not in ccd_metadata_dict:
                            ccd_metadata_dict[ccd_name] = metadata
                            ccd_generator_map[ccd_name] = gen_id
                        
                        try_dispatch(gen_id)

            except asyncio.TimeoutError:
                # Check all generators for free slots (e.g. if they finished tasks but we missed it? Unlikely)
                # Or just to be safe.
                for generator in generator_list:
                    try_dispatch(generator.id)

    finally:
        del _message_dispatcher[job.id]
        # We do NOT close the RPC connections.

    dist_config = CcdDistributionConfig(ccd_generator_map, generators)
    async with job.watcher.notify_shared_large_status():
        job.shared_large_status.dist_config = dist_config
        job.shared_large_status.ccd_metadata_list = [*ccd_metadata_dict.values()]

    await rpc_scatter(_save_job_metadata_rpc, job)
    await rpc_scatter(_save_ccd_distribution_config_rpc, job, dist_config)

    return [*ccd_metadata_dict.values()]


def _generate_tiles_with_queue(rpc_queue: queue.Queue[tuple[Job, CcdDataRef] | None]):
    """
    ジェネレータプロセスで実行される RPC 関数。
    queueから動的にCCDを取得して処理する。
    """
    def items_generator():
        while True:
            item = rpc_queue.get()
            if item is None:
                break
            yield item

    yield from generate_single_fits_tiles_pipeline(items_generator())


def _save_job_metadata_rpc(job: Job) -> None:
    """ジョブのメタデータをローカルストレージに保存。"""
    job.local_storage.metadata.save()


def _save_ccd_distribution_config_rpc(job: Job, dist_config: CcdDistributionConfig) -> None:
    """CCD とジェネレータの対応関係をローカルストレージに保存。"""
    job.local_storage.ccd_distribution_config.save(dist_config)
