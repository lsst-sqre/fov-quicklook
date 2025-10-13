import asyncio
from dataclasses import dataclass
from functools import lru_cache
from typing import Any, Awaitable, Callable, Generic, TypeVar

from quicklook.comm.coordinator import get_available_generators, remove_generator
from quicklook.comm.types import GeneratorId, GeneratorInfo
from quicklook.config import config
from quicklook.rpc import Rpc as RpcClient
from quicklook.utils.adaptive_map import MapResult, Worker, WorkerDown, adaptive_map, create_worker


T = TypeVar("T")


@dataclass
class Rpc(Generic[T]):
    """RPCリクエストを表すデータクラス"""

    function: Callable[..., T]
    args: tuple = ()
    kwargs: dict | None = None

    @classmethod
    def create(cls, target: Callable, *args, **kwargs) -> "Rpc":
        return cls(function=target, args=args, kwargs=kwargs)


async def run_rpc(url: str, rpc: Rpc[T]) -> T:
    """RPCを実行し、結果を返す"""
    kwargs = rpc.kwargs or {}
    ws_url = _convert_http_to_ws_url(url)
    result = await RpcClient(ws_url, rpc.function, *rpc.args, **kwargs).run()
    if hasattr(result, "__aiter__"):
        # ジェネレータの場合は最初の値を返す（ただし通常は run_rpc_stream を使うべき）
        async for item in result:  # type: ignore[union-attr]
            return item  # type: ignore[return-value]
        raise RuntimeError("No result returned from RPC")
    return result  # type: ignore[return-value]


async def run_rpc_stream(url: str, rpc: Rpc[T]):
    """RPCを実行し、結果をストリームで返す"""
    kwargs = rpc.kwargs or {}
    ws_url = _convert_http_to_ws_url(url)
    result = await RpcClient(ws_url, rpc.function, *rpc.args, **kwargs).run()
    if hasattr(result, "__aiter__"):
        async for item in result:  # type: ignore[union-attr]
            yield item
    else:
        if result is not None:
            yield result


def _convert_http_to_ws_url(url: str) -> str:
    """HTTPのURLをWebSocketのURLに変換"""
    if url.startswith("http://"):
        return "ws://" + url[7:]
    elif url.startswith("https://"):
        return "wss://" + url[8:]
    return url


async def adaptive_map_rpc(
    rpcs: list[Rpc],
    *,
    on_yield: Callable[[Any], Awaitable] | None = None,
    stream: bool = False,
):
    assert on_yield and stream or not stream, f"Invalid combination of on_progress and stream"
    ctx = _Context(stream=stream, on_yield=on_yield, alive=True)
    items = [_Item(rpc=rpc, ctx=ctx) for rpc in rpcs]
    workers = _get_rpc_workers()
    try:
        async for result in adaptive_map(
            workers,
            items,
            cancel_on_reschedule=False,
        ):
            yield _MapResult.wrap(result)
    finally:
        ctx.alive = False


def _get_rpc_workers() -> list[Worker]:
    gs = get_available_generators()
    workers = [_worker_from_generator(g) for g in gs.values()]
    return workers


@dataclass
class _MapResult:
    value: Any
    args: tuple
    generator_id: str

    @classmethod
    def wrap(cls, original: MapResult):
        item: _Item = original.item
        return _MapResult(
            value=original.value,
            args=item.rpc.args,
            generator_id=original.worker.id(),
        )


@dataclass
class _Context:
    stream: bool
    on_yield: Callable[[Any], Awaitable] | None
    alive: bool


@dataclass
class _Item:
    rpc: Rpc
    ctx: _Context


@dataclass
class YieledValue(Generic[T]):
    value: T
    generator_id: GeneratorId
    args: tuple


@lru_cache(maxsize=256)  # lru_cacheを使っているのは、Workerはcapacityを保持するため。
def _worker_from_generator(g: GeneratorInfo):
    async def process_item(item: _Item):
        ctx = item.ctx
        try:
            if ctx.stream:
                async for value in run_rpc_stream(f'{g.url}/rpc', item.rpc):
                    if ctx.alive and ctx.on_yield:  # pragma: no branch
                        await ctx.on_yield(YieledValue(value, g.id, item.rpc.args))
            else:
                return await run_rpc(f'{g.url}/rpc', item.rpc)
        except TimeoutError:  # pragma: no cover
            raise WorkerDown()

    async def teardown():  # pragma: no cover
        remove_generator(g)

    return create_worker(
        id=g.id,
        process_item=process_item,
        teardown=teardown,
        max_concurrency=config.generator_max_concurrent_jobs,
    )


async def rpc_scatter(
    rpc: Rpc,
    on_yield: Callable[[Any], Awaitable] | None = None,
    stream: bool = False,
):
    assert on_yield and stream or not stream, f"Invalid combination of on_progress and stream"

    async def single(g: GeneratorInfo):
        if stream:
            async for value in run_rpc_stream(f'{g.url}/rpc', rpc):
                if on_yield:  # pragma: no branch
                    await on_yield(YieledValue(value, g.id, rpc.args))
        else:
            return await run_rpc(f'{g.url}/rpc', rpc)

    return await asyncio.gather(*[single(g) for g in get_available_generators().values()])


def rpc_endpoint(generator_id: str) -> GeneratorId:
    return get_available_generators()[GeneratorId(generator_id)].id
