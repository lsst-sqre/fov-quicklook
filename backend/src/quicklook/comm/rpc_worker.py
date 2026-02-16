import asyncio
from collections.abc import Generator
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, ParamSpec, TypeVar

import quicklook.mylogging
from quicklook.comm.coordinator import get_available_generators
from quicklook.comm.types import GeneratorId, GeneratorInfo
from quicklook.rpc import Rpc as RpcClient

logger = quicklook.mylogging.getLogger(__name__)

P = ParamSpec('P')
R = TypeVar('R')


@dataclass
class YieledValue:
    value: Any
    generator_id: GeneratorId
    args: tuple


class GeneratorUnavailableError(Exception):
    """Generatorが利用不可能な場合のエラー"""
    def __init__(self, generator_id: GeneratorId, cause: Exception):
        self.generator_id = generator_id
        self.cause = cause
        super().__init__(f"Generator {generator_id} unavailable: {cause}")


async def rpc_scatter(
    func: Callable[P, R],
    *args: P.args,
    **kwargs: P.kwargs,
) -> list[R]:
    """
    全てのジェネレータに対して同じRPC関数を並列実行し、結果を返す

    1台のGenerator失敗はログに記録されるが、他のGeneratorの結果は正常に返される。

    Args:
        func: 実行するRPC関数（非ジェネレータ関数）
        *args: 関数の位置引数
        **kwargs: 関数のキーワード引数

    Returns:
        各ジェネレータからの戻り値のリスト（失敗したGeneratorは除外）
    """
    generators = get_available_generators()

    async def single(g: GeneratorInfo) -> R:
        ws_url = f'{g.ws_url}/rpc'
        return await RpcClient(ws_url, func, *args, **kwargs).run()  # type: ignore[return-value]

    results = await asyncio.gather(*[single(g) for g in generators.values()], return_exceptions=True)

    successful_results: list[R] = []
    for g, result in zip(generators.values(), results):
        if isinstance(result, BaseException):
            logger.error(f"RPC scatter failed for generator {g.id}: {result}")
        else:
            successful_results.append(result)

    return successful_results


async def rpc_scatter_stream(
    on_yield: Callable[[YieledValue], Awaitable],
    func: Callable[P, Generator[R, Any, Any]],
    *args: P.args,
    **kwargs: P.kwargs,
) -> None:
    """
    全てのジェネレータに対して同じRPC関数を並列実行し、ストリーム結果を処理する

    1台のGenerator失敗はログに記録されるが、他のGeneratorの処理は継続される。

    Args:
        on_yield: 各yield値に対するコールバック
        func: 実行するRPC関数（ジェネレータ関数）
        *args: 関数の位置引数
        **kwargs: 関数のキーワード引数

    Returns:
        None（結果はon_yieldで処理される）
    """
    generators = get_available_generators()

    async def single(g: GeneratorInfo) -> None:
        try:
            ws_url = f'{g.ws_url}/rpc'
            async for value in RpcClient(ws_url, func, *args, **kwargs).iterate():
                await on_yield(YieledValue(value, g.id, args))
        except Exception as e:
            logger.error(f"RPC scatter stream failed for generator {g.id}: {e}")

    await asyncio.gather(*[single(g) for g in generators.values()])
