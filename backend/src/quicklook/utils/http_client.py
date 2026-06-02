"""
aiohttp ClientSession の再利用ユーティリティ。

各プロセス（Coordinator / Generator / Frontend）で1つのセッションを共有する。
lifespan で初期化・後始末し、利用側は get_session() で取得する。
"""

import socket
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import aiohttp

from quicklook.config import config


_session: aiohttp.ClientSession | None = None


@asynccontextmanager
async def managed_session() -> AsyncIterator[None]:
    """
    aiohttp.ClientSession のライフサイクルを管理するコンテキストマネージャ。

    FastAPI の lifespan 内で使用する::

        @asynccontextmanager
        async def lifespan(app):
            async with managed_session():
                yield

    ネスト呼び出しは安全（外側のセッションが使われる）。
    """
    global _session
    if _session is not None:
        yield
        return

    connector = aiohttp.TCPConnector(
        family=socket.AF_INET,
        limit=config.http_client_connection_limit,
        ttl_dns_cache=config.http_client_dns_cache_ttl,
        keepalive_timeout=config.http_client_keepalive_timeout,
    )
    _session = aiohttp.ClientSession(connector=connector)
    try:
        yield
    finally:
        await _session.close()
        _session = None


def get_session() -> aiohttp.ClientSession:
    """
    現在のプロセスの共有 ClientSession を取得する。

    managed_session() コンテキスト外で呼ばれた場合は RuntimeError。
    """
    if _session is None:
        raise RuntimeError(
            "aiohttp ClientSession is not initialized. "
            "Ensure managed_session() is used in the application lifespan."
        )
    return _session
