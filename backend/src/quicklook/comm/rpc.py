"""
RPC (Remote Procedure Call) モジュール。

このモジュールは、ネットワーク経由で関数を呼び出すためのRPC機能を提供します。
クライアント側ではRPCリクエストを作成し、サーバーに送信して結果を受け取ります。
サーバー側では受信したRPCをローカルで実行し、結果をストリームで返します。

WebSocketベースのRPC実装を使用しています。

注: このモジュールは後方互換性のために残されており、
内部では quicklook.rpc モジュールを使用しています。
"""

import pickle
from dataclasses import dataclass
from logging import getLogger
from types import GeneratorType
from typing import Any, AsyncGenerator, Callable, Generator, Generic, ParamSpec, TypeVar

import aiohttp

from quicklook.rpc.client import Rpc as RpcClient
from quicklook.rpc.types import RpcRemoteError as _RpcRemoteError
from quicklook.config import config

timeout_total = config.rpc_timeout_total
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
    url: str,
    rpc: Rpc[T],
    *,
    timeout: aiohttp.ClientTimeout | None = None,
) -> T:
    """RPCを実行し、単一の結果を返す。

    指定されたURLのRPCサーバーにリクエストを送信し、
    ストリームから最初の結果を取得して返します。
    結果がない場合はRuntimeErrorを発生させます。
    """
    async for result in run_rpc_stream(url, rpc, timeout=timeout):  # pragma: no branch
        return result
    raise RuntimeError("No result returned from RPC")  # pragma: no cover


async def run_rpc_stream(
    url: str,
    rpc: Rpc[T],
    *,
    timeout: aiohttp.ClientTimeout | None = None,
) -> AsyncGenerator[T, None]:
    """RPCを実行し、結果をストリームで返す。

    WebSocketベースのRPCを使用して関数を実行し、結果をストリームで受け取ります。
    結果は非同期ジェネレータとしてyieldされます。
    
    エラーが発生した場合でも、それまでにyieldされた値は取得できます。
    """
    # HTTPのURLをWebSocketのURLに変換
    ws_url = _convert_http_to_ws_url(url)
    
    kwargs = rpc.kwargs or {}
    
    try:
        # 新しいrpcモジュールを使用
        rpc_client = RpcClient(ws_url, rpc.function, *rpc.args, **kwargs)
        result = await rpc_client.run()
        
        # 結果がAsyncIteratorの場合
        if hasattr(result, '__aiter__'):
            async for item in result:  # type: ignore[union-attr]
                yield item
        else:
            # 単一の値の場合
            if result is not None:
                yield result  # type: ignore[misc]
    except _RpcRemoteError as e:
        # 新しいrpcモジュールのRpcRemoteErrorを互換性のある形式に変換
        try:
            exception_class = eval(e.error_type, {"__builtins__": __builtins__})
            if not issubclass(exception_class, Exception):
                raise TypeError()
        except (NameError, TypeError):
            exception_class = Exception
        
        original_exception: Exception = exception_class(e.error_message)
        raise RpcRemoteError(original_exception) from e


def _convert_http_to_ws_url(url: str) -> str:
    """HTTPのURLをWebSocketのURLに変換する。
    
    例: http://localhost:8000/rpc -> ws://localhost:8000/rpc
    """
    if url.startswith('http://'):
        return 'ws://' + url[7:]
    elif url.startswith('https://'):
        return 'wss://' + url[8:]
    else:
        # すでにws://またはwss://の場合はそのまま
        return url


class RpcRemoteError(RuntimeError):
    def __init__(self, exception: Exception):
        super().__init__(str(exception))
        self.exception = exception


def create_rpc_caller_endpoint(body: bytes) -> Generator[bytes, None, None]:
    """RPCサーバー側で呼び出されるエンドポイント関数。

    受信したバイトデータをRPCリクエストとしてデシリアライズし、
    ローカルで関数を実行して結果をシリアライズしてyieldします。
    ジェネレータの場合は各アイテムを個別にyieldします。
    
    注: この関数は後方互換性のために残されていますが、
    新しいWebSocketベースのRPCではサーバー側の実装は
    quicklook.rpc.server.create_rpc_endpoint を使用してください。
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
