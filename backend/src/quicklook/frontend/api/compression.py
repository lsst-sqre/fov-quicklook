import gzip
from typing import Awaitable, Callable

from fastapi import FastAPI, Request, Response

# ファイルパスをキーとして圧縮済みコンテンツを保存するキャッシュ


def setup_compression(app: FastAPI, static_prefix: str) -> None:  # pragma: no cover
    """
    Setup compression middleware for the FastAPI application:
    - Compress JSON responses
    - Compress responses for paths starting with static_prefix
    - Cache compressed results for static paths
    - Only compress if client supports gzip
    """

    async def custom_compression_middleware(request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        response = await call_next(request)

        # Check if client supports gzip compression
        accept_encoding = request.headers.get("Accept-Encoding", "")
        client_accepts_gzip = "gzip" in accept_encoding

        # Check if the path starts with static_prefix
        is_static_path = request.url.path.startswith(static_prefix)
        # Check if response is JSON
        is_json = response.headers.get("content-type", "").lower().startswith("application/json")

        if client_accepts_gzip and (is_static_path or is_json):
            response_body = b""
            async for chunk in response.body_iterator:  # type: ignore
                response_body += chunk

            if is_static_path:
                # キャッシュを利用して静的ファイルの圧縮処理を最適化
                file_path = request.url.path
                compressed_body = get_compressed_content(file_path, response_body)
            else:
                # JSONレスポンスは毎回圧縮（キャッシュしない）
                compressed_body = gzip.compress(response_body)

            # Set new response with compressed content
            response = Response(content=compressed_body, status_code=response.status_code, headers=dict(response.headers), media_type=response.media_type)
            response.headers["Content-Encoding"] = "gzip"
            response.headers["Content-Length"] = str(len(compressed_body))

        return response

    app.middleware("http")(custom_compression_middleware)


def get_compressed_content(file_path: str, content: bytes) -> bytes:
    """
    Compress content and cache the result using file path as the cache key.

    Args:
        file_path: The path of the file used as cache key
        content: The content to compress

    Returns:
        The compressed content
    """
    # ファイルパスをキーとしてキャッシュをチェック
    if file_path not in _compressed_content_cache:
        _compressed_content_cache[file_path] = gzip.compress(content)

    return _compressed_content_cache[file_path]


_compressed_content_cache: dict[str, bytes] = {}
