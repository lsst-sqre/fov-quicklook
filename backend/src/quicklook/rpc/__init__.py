"""
RPC2 - WebSocket ベースのリモートプロシージャコール実装

このモジュールはノード間でのリモート関数呼び出しを簡潔に記述できるように設計されています。
"""

from .client import Rpc
from .lifespan import rpc_lifespan
from .queue import _RpcQueue
from .server import create_rpc_endpoint
from .types import RpcRemoteError

__all__ = [
    "Rpc",
    "_RpcQueue",
    "RpcRemoteError",
    "rpc_lifespan",
    "create_rpc_endpoint",
]
