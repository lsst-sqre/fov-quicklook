import asyncio
from dataclasses import dataclass
from typing import Any, Awaitable, Callable

from quicklook.comm.coordinator import get_available_generators
from quicklook.comm.types import GeneratorId, GeneratorInfo
from quicklook.rpc import Rpc as RpcClient


@dataclass
class YieledValue:
    value: Any
    generator_id: GeneratorId
    args: tuple


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
        ws_url = f'{g.ws_url}/rpc'
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
