"""
RPC (Remote Procedure Call) モジュール。

このモジュールは、ネットワーク経由で関数を呼び出すためのRPC機能を提供します。
クライアント側ではRPCリクエストを作成し、サーバーに送信して結果を受け取ります。
サーバー側では受信したRPCをローカルで実行し、結果をストリームで返します。
"""

import inspect
import pickle
from dataclasses import dataclass
from logging import getLogger
from types import AsyncGeneratorType, GeneratorType
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
    def create(cls, func: Callable[P, T], *args: P.args, **kwargs: P.kwargs) -> 'Rpc[T]':
        """RPCリクエストを作成するクラスメソッド。

        指定された関数と引数からRpcインスタンスを生成します。
        """
        return cls(function=func, args=args, kwargs=kwargs)


async def run_rpc(
    url: str,
    rpc: Rpc[T],
    *,
    timeout: aiohttp.ClientTimeout = aiohttp.ClientTimeout(total=1),
) -> T:
    """RPCを実行し、単一の結果を返す。

    指定されたURLのRPCサーバーにリクエストを送信し、
    ストリームから最初の結果を取得して返します。
    結果がない場合はRuntimeErrorを発生させます。
    """
    async for result in run_rpc_stream(url, rpc, timeout=timeout):
        return result
    raise RuntimeError("No data received from RPC")


async def run_rpc_stream(
    url: str,
    rpc: Rpc[T],
    *,
    timeout: aiohttp.ClientTimeout = aiohttp.ClientTimeout(total=1),
) -> AsyncGenerator[T, None]:
    """RPCを実行し、結果をストリームで返す。

    外部のRPCサーバーに接続し、RPCを実行して結果をストリームで受け取ります。
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


async def create_rpc_caller_endpoint_async(body: bytes) -> AsyncGenerator[bytes, None]:
    """RPCサーバー側で呼び出される非同期エンドポイント関数。

    受信したバイトデータをRPCリクエストとしてデシリアライズし、
    ローカルで関数を実行して結果をシリアライズしてyieldします。
    非同期ジェネレータと通常のジェネレータの両方に対応します。
    """
    rpc: Rpc = pickle.loads(body)

    async def g():
        kwargs = rpc.kwargs or {}
        try:
            # 非同期関数かどうかをチェック
            if inspect.iscoroutinefunction(rpc.function):
                result = await rpc.function(*rpc.args, **kwargs)
            else:
                result = rpc.function(*rpc.args, **kwargs)
                
            if isinstance(result, AsyncGeneratorType):
                async for item in result:
                    yield item
            elif isinstance(result, GeneratorType):
                for item in result:
                    yield item
            else:
                yield result
        except Exception as e:
            log_rpc_error(rpc, e)
            yield e

    async for item in g():
        yield serialize_with_size(item)


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
    except TypeError as e:
        # logger.exception(f"Failed to pickle object: {repr(obj)} - {repr(e)}")
        if isinstance(obj, Exception):
            pickled_data = pickle.dumps(PickleError(repr(obj)))
        else:
            raise
    return len(pickled_data).to_bytes(4, 'big') + pickled_data


class PickleError(RuntimeError):
    """pickle操作中のエラーを表す例外クラス。"""
    pass
