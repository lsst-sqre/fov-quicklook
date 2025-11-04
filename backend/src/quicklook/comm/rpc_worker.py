import asyncio
from collections.abc import Generator
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, ParamSpec, TypeVar

from quicklook.comm.coordinator import get_available_generators
from quicklook.comm.types import GeneratorId, GeneratorInfo
from quicklook.rpc import Rpc as RpcClient

P = ParamSpec('P')
R = TypeVar('R')


@dataclass
class YieledValue:
    value: Any
    generator_id: GeneratorId
    args: tuple


async def rpc_scatter(
    func: Callable[P, R],
    *args: P.args,
    **kwargs: P.kwargs,
) -> list[R]:
    """
    全てのジェネレータに対して同じRPC関数を並列実行し、結果を返す

    Args:
        func: 実行するRPC関数（非ジェネレータ関数）
        *args: 関数の位置引数
        **kwargs: 関数のキーワード引数

    Returns:
        各ジェネレータからの戻り値のリスト
    """

    async def single(g: GeneratorInfo) -> R:
        ws_url = f'{g.ws_url}/rpc'
        return await RpcClient(ws_url, func, *args, **kwargs).run()  # type: ignore[return-value]

    return await asyncio.gather(*[single(g) for g in get_available_generators().values()])


async def rpc_scatter_stream(
    on_yield: Callable[[YieledValue], Awaitable],
    func: Callable[P, Generator[R, Any, Any]],
    *args: P.args,
    **kwargs: P.kwargs,
) -> None:
    """
    全てのジェネレータに対して同じRPC関数を並列実行し、ストリーム結果を処理する

    Args:
        on_yield: 各yield値に対するコールバック
        func: 実行するRPC関数（ジェネレータ関数）
        *args: 関数の位置引数
        **kwargs: 関数のキーワード引数

    Returns:
        None（結果はon_yieldで処理される）
    """

    async def single(g: GeneratorInfo) -> None:
        ws_url = f'{g.ws_url}/rpc'
        async for value in RpcClient(ws_url, func, *args, **kwargs).iterate():
            await on_yield(YieledValue(value, g.id, args))

    await asyncio.gather(*[single(g) for g in get_available_generators().values()])
