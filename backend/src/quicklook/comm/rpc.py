"""
RPC (Remote Procedure Call) モジュール。

このモジュールは、ネットワーク経由で関数を呼び出すためのRPC機能を提供します。
クライアント側ではRPCリクエストを作成し、サーバーに送信して結果を受け取ります。
サーバー側では受信したRPCをローカルで実行し、結果をストリームで返します。
"""

import pickle
from dataclasses import dataclass
from logging import getLogger
from types import GeneratorType
from typing import Any, AsyncGenerator, Callable, Generator, Generic, ParamSpec, TypeVar

import aiohttp

from quicklook.utils.iterutils import async_bytes_iterator_to_stream

logger = getLogger(__name__)

P = ParamSpec('P')
T = TypeVar('T')


@dataclass
class Rpc(Generic[T]):
    """RPCリクエストを表すデータクラス。

    呼び出す関数とその引数を保持します。
    """

    function: Callable[..., T]
    args: tuple = ()
    kwargs: dict | None = None

    @classmethod
    def create(cls, target: Callable[P, T], *args: P.args, **kwargs: P.kwargs) -> 'Rpc[T]':
        """RPCリクエストを作成するクラスメソッド。

        指定された関数と引数からRpcインスタンスを生成します。
        """
        return cls(function=target, args=args, kwargs=kwargs)


async def run_rpc(
    url,
    rpc: Rpc[T],
    *,
    timeout: aiohttp.ClientTimeout = aiohttp.ClientTimeout(total=60),
) -> T:
    """RPCを実行し、単一の結果を返す。

    指定されたURLのRPCサーバー、TestClient、またはendpointにリクエストを送信し、
    ストリームから最初の結果を取得して返します。
    結果がない場合はRuntimeErrorを発生させます。
    """
    async for result in run_rpc_stream(url, rpc, timeout=timeout):
        return result
    raise RuntimeError("No result returned from RPC")


async def run_rpc_stream(
    url: str,
    rpc: Rpc[T],
    *,
    timeout: aiohttp.ClientTimeout = aiohttp.ClientTimeout(total=60),
) -> AsyncGenerator[T, None]:
    """RPCを実行し、結果をストリームで返す。

    外部のRPCサーバー、TestClient、またはendpointに接続し、RPCを実行して結果をストリームで受け取ります。
    結果は非同期ジェネレータとしてyieldされます。
    """
    # RPCリクエストをpickleでシリアライズ
    pickled_rpc = pickle.dumps(rpc)

    async with aiohttp.ClientSession() as session:
        async with session.post(
            url,
            data=pickled_rpc,
            timeout=timeout,
        ) as response:
            response.raise_for_status()
            read = async_bytes_iterator_to_stream(response.content.iter_chunked(8192))
            while True:
                size_bytes = await read(4)
                if len(size_bytes) < 4:
                    break
                size = int.from_bytes(size_bytes, 'big')
                data = await read(size)
                result = pickle.loads(data)
                if isinstance(result, Exception):
                    raise result
                yield result


def create_rpc_caller_endpoint(body: bytes) -> Generator[bytes, None, None]:
    """RPCサーバー側で呼び出されるエンドポイント関数。

    受信したバイトデータをRPCリクエストとしてデシリアライズし、
    ローカルで関数を実行して結果をシリアライズしてyieldします。
    ジェネレータの場合は各アイテムを個別にyieldします。
    """
    rpc: Rpc = pickle.loads(body)

    def g():
        kwargs = rpc.kwargs or {}
        try:
            result = rpc.function(*rpc.args, **kwargs)
            if isinstance(result, GeneratorType):
                for item in result:
                    yield item
            else:
                yield result
        except Exception as e:
            log_rpc_error(rpc, e)
            yield e

    yield from (serialize_with_size(item) for item in g())


def log_rpc_error(rpc: Rpc, error: Exception) -> None:
    """RPC実行エラーをログに記録。

    RPC呼び出しの詳細と例外情報をエラーログに出力します。
    """
    kwargs = rpc.kwargs or {}
    args_str = ', '.join(map(str, rpc.args))
    kwargs_str = ', '.join(f'{k}={v}' for k, v in kwargs.items())
    logger.error(f"RPC call failed: {rpc.function.__name__}({args_str}, {kwargs_str})")
    logger.error(f"Exception: {error}", exc_info=True)


def serialize_with_size(obj: Any) -> bytes:
    """オブジェクトをpickleし、サイズ前置でシリアライズ。

    オブジェクトをpickleでバイト列に変換し、
    先頭に4バイトのサイズ情報を付加して返します。
    pickleに失敗した場合はPickleErrorをpickleします。
    """
    try:
        pickled_data = pickle.dumps(obj)
    except TypeError as e:  # pragma: no cover
        # logger.exception(f"Failed to pickle object: {repr(obj)} - {repr(e)}")
        if isinstance(obj, Exception):
            pickled_data = pickle.dumps(PickleError(repr(obj)))
        else:
            raise
    return len(pickled_data).to_bytes(4, 'big') + pickled_data


class PickleError(RuntimeError):
    """pickle操作中のエラーを表す例外クラス。"""

    pass
