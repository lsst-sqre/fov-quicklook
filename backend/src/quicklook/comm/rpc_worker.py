import asyncio
from dataclasses import dataclass
from functools import lru_cache
from typing import Any, Awaitable, Callable

from quicklook.comm.coordinator import get_available_generators, remove_generator
from quicklook.comm.types import GeneratorId, GeneratorInfo
from quicklook.config import config
from quicklook.rpc import Rpc as RpcClient
from quicklook.utils.adaptive_map import MapResult, Worker, WorkerDown, adaptive_map, create_worker


def _convert_http_to_ws_url(url: str) -> str:
    """HTTPのURLをWebSocketのURLに変換"""
    if url.startswith("http://"):
        return "ws://" + url[7:]
    elif url.startswith("https://"):
        return "wss://" + url[8:]
    return url


@dataclass
class YieledValue:
    value: Any
    generator_id: GeneratorId
    args: tuple


@dataclass
class _AdaptiveMapContext:
    """adaptive_map_rpcの共有コンテキスト"""
    alive: bool = True


@dataclass
class _RpcTask:
    """adaptive_map用のRPCタスク"""
    func: Callable
    args: tuple
    kwargs: dict
    stream: bool
    on_yield: Callable[[YieledValue], Awaitable] | None
    ctx: _AdaptiveMapContext


@dataclass
class _MapResultWrapper:
    """adaptive_mapの結果をラップ"""
    value: Any
    args: tuple
    generator_id: str

    @classmethod
    def wrap(cls, original: MapResult):
        task: _RpcTask = original.item
        return _MapResultWrapper(
            value=original.value,
            args=task.args,
            generator_id=original.worker.id(),
        )


@lru_cache(maxsize=256)
def _worker_from_generator(g: GeneratorInfo):
    """ジェネレータからWorkerを作成（キャッシュ付き）"""
    async def process_item(item: _RpcTask):
        ws_url = _convert_http_to_ws_url(f'{g.url}/rpc')
        result = await RpcClient(ws_url, item.func, *item.args, **item.kwargs).run()
        
        try:
            if item.stream:
                if hasattr(result, "__aiter__"):
                    async for value in result:  # type: ignore[union-attr]
                        if item.ctx.alive and item.on_yield:  # pragma: no branch
                            await item.on_yield(YieledValue(value, g.id, item.args))
                else:
                    if result is not None and item.ctx.alive and item.on_yield:
                        await item.on_yield(YieledValue(result, g.id, item.args))
            else:
                # 非ストリームモードでは結果を返す
                if hasattr(result, "__aiter__"):
                    async for item_value in result:  # type: ignore[union-attr]
                        return item_value
                    raise RuntimeError("No result returned from RPC")
                return result
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


async def adaptive_map_rpc(
    func: Callable,
    items: list[tuple],
    *,
    on_yield: Callable[[YieledValue], Awaitable] | None = None,
    stream: bool = False,
):
    """
    複数のRPCタスクをジェネレータ間で動的に分配して並列実行する
    
    Args:
        func: 実行するRPC関数
        items: 各RPCタスクの引数のリスト（各要素はtupleで、funcの引数として展開される）
        on_yield: ストリーム時の各yield値に対するコールバック
        stream: ストリームモード（True: ジェネレータ関数、False: 通常関数）
    
    Yields:
        各タスクの実行結果（_MapResultWrapper）
    """
    assert on_yield and stream or not stream, "stream=True requires on_yield callback"
    
    # 共有コンテキスト
    ctx = _AdaptiveMapContext()
    
    # RPCタスクを作成
    tasks = [
        _RpcTask(
            func=func,
            args=args,
            kwargs={},
            stream=stream,
            on_yield=on_yield,
            ctx=ctx,
        )
        for args in items
    ]
    
    # ジェネレータからWorkerを作成
    gs = get_available_generators()
    workers = [_worker_from_generator(g) for g in gs.values()]
    
    try:
        async for result in adaptive_map(
            workers,
            tasks,
            cancel_on_reschedule=False,
        ):
            yield _MapResultWrapper.wrap(result)
    finally:
        # ストリーミングを停止
        ctx.alive = False


async def rpc_scatter(
    func: Callable,
    *,
    args: tuple = (),
    kwargs: dict | None = None,
    on_yield: Callable[[YieledValue], Awaitable] | None = None,
    stream: bool = False,
):
    """
    全てのジェネレータに対して同じRPC関数を並列実行する
    
    Args:
        func: 実行するRPC関数
        args: 関数の位置引数
        kwargs: 関数のキーワード引数
        on_yield: ストリーム時の各yield値に対するコールバック
        stream: ストリームモード（True: ジェネレータ関数、False: 通常関数）
    
    Returns:
        stream=Falseの場合、各ジェネレータからの戻り値のリスト
        stream=Trueの場合、Noneを返す（結果はon_yieldで処理される）
    """
    assert on_yield and stream or not stream, "stream=True requires on_yield callback"
    
    if kwargs is None:
        kwargs = {}

    async def single(g: GeneratorInfo):
        ws_url = _convert_http_to_ws_url(f'{g.url}/rpc')
        result = await RpcClient(ws_url, func, *args, **kwargs).run()
        
        if stream:
            if hasattr(result, "__aiter__"):
                async for value in result:  # type: ignore[union-attr]
                    if on_yield:  # pragma: no branch
                        await on_yield(YieledValue(value, g.id, args))
            else:
                # 単一の値の場合もon_yieldで返す
                if result is not None and on_yield:
                    await on_yield(YieledValue(result, g.id, args))
        else:
            # 非ストリームモードでは結果を返す
            if hasattr(result, "__aiter__"):
                # ジェネレータの場合は最初の値を返す
                async for item in result:  # type: ignore[union-attr]
                    return item
                raise RuntimeError("No result returned from RPC")
            return result

    return await asyncio.gather(*[single(g) for g in get_available_generators().values()])


def rpc_endpoint(generator_id: str) -> GeneratorId:
    return get_available_generators()[GeneratorId(generator_id)].id
