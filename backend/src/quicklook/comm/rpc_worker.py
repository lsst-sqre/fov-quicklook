import asyncio
from dataclasses import dataclass
from functools import lru_cache
from typing import Any, Callable

from quicklook.comm.coordinator import get_available_generators, remove_generator
from quicklook.comm.types import GeneratorInfo
from quicklook.config import config
from quicklook.comm.rpc import Rpc, run_rpc, run_rpc_stream
from quicklook.utils.adaptive_map import MapResult, Worker, WorkerDown, adaptive_map, create_worker


@dataclass
class MapRpcResult:
    value: Any
    rpc_args: tuple
    generator_id: str


def _noop(result: MapRpcResult):
    pass


async def adaptive_map_rpc(
    rpcs: list[Rpc],
    *,
    on_progress: Callable[[Any], None] | None = None,
    stream: bool = False,
    on_late_result: Callable[[MapRpcResult], None] = _noop,
):
    assert on_progress and stream or not stream, f"Invalid combination of on_progress and stream"

    def on_late_result2(r: MapResult):
        return on_late_result(_convert_map_result(r))

    items = [_Item(rpc=rpc, on_progress=on_progress, stream=stream) for rpc in rpcs]
    workers = _get_rpc_workers()
    async for result in adaptive_map(
        workers,
        items,
        cancel_on_reschedule=False,
        on_late_result=on_late_result2,
    ):
        yield _convert_map_result(result)


async def rpc_scatter(rpc: Rpc):
    async def single(rpc_url: str):
        await run_rpc(f'{rpc_url}/rpc', rpc)

    await asyncio.gather(*[single(g.url) for g in get_available_generators().values()])


def rpc_endpoint(generator_id: str):
    return get_available_generators()[generator_id].id


def _convert_map_result(original: MapResult):
    item: _Item = original.item
    return MapRpcResult(
        value=original.value,
        rpc_args=item.rpc.args,
        generator_id=original.worker.id(),
    )


def _get_rpc_workers() -> list[Worker]:
    gs = get_available_generators()
    workers = [_worker_from_generator(g) for g in gs.values()]
    return workers


@dataclass
class _Item:
    rpc: Rpc
    stream: bool
    on_progress: Callable[[Any], None] | None


@lru_cache(maxsize=256)  # cacheを使っているのは、Workerはcapacityを保持するため。
def _worker_from_generator(g: GeneratorInfo):
    async def process_item(item: _Item):
        try:
            if item.stream:
                async for progress in run_rpc_stream(f'{g.url}/rpc', item.rpc):
                    if item.on_progress:
                        item.on_progress(progress)
            else:
                return await run_rpc(f'{g.url}/rpc', item.rpc)
        except TimeoutError:
            raise WorkerDown

    async def teardown():
        remove_generator(g)

    return create_worker(
        id=g.id,
        process_item=process_item,
        teardown=teardown,
        max_concurrency=config.generator_max_concurrent_jobs,
    )
