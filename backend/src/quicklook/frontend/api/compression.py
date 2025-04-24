import gzip
import logging
from typing import Awaitable, Callable

from fastapi import FastAPI, Request, Response

# ファイルパスをキーとして圧縮済みコンテンツを保存するキャッシュ

logger = logging.getLogger(f"uvicorn.{__name__}")
# logger.setLevel(logging.DEBUG)


def setup_compression(app: FastAPI, static_prefix: str) -> None:  # pragma: no cover
    """
    Setup compression middleware for the FastAPI application:
    - Compress JSON responses
    - Compress responses for paths starting with static_prefix
    - Cache compressed results for static paths
    - Only compress if client supports gzip
    """

    async def custom_compression_middleware(request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        logger.warning(f"Processing request: {request.method} {request.url.path}")
        response = await call_next(request)

        # Check if compression should be applied
        if should_compress_response(request, response, static_prefix):
            response = await compress_response(request, response, static_prefix)
        else:
            logger.warning(f"Skipping compression, conditions not met. Status: {response.status_code}")

        return response

    app.middleware("http")(custom_compression_middleware)


def should_compress_response(request: Request, response: Response, static_prefix: str) -> bool:
    """
    Determine if response should be compressed.
    
    Args:
        request: The FastAPI request object
        response: The FastAPI response object
        static_prefix: Prefix for static content paths
        
    Returns:
        True if the response should be compressed
    """
    # Check if client supports gzip compression
    accept_encoding = request.headers.get("Accept-Encoding", "")
    client_accepts_gzip = "gzip" in accept_encoding
    logger.warning(f"Client accepts gzip: {client_accepts_gzip}, Accept-Encoding: {accept_encoding}")

    # Check if the path starts with static_prefix
    is_static_path = request.url.path.startswith(static_prefix)
    # Check if response is JSON
    is_json = response.headers.get("content-type", "").lower().startswith("application/json")

    logger.warning(f"Response type - static: {is_static_path}, JSON: {is_json}, Content-Type: {response.headers.get('content-type')}")
    
    return client_accepts_gzip and (is_static_path or is_json)


async def compress_response(request: Request, response: Response, static_prefix: str) -> Response:
    """
    Compress response content with gzip.
    
    Args:
        request: The FastAPI request object
        response: The FastAPI response object
        static_prefix: Prefix for static content paths
        
    Returns:
        Compressed response
    """
    # Collect response body
    response_body = await get_response_body(response)
    original_size = len(response_body)
    logger.warning(f"Original response size: {original_size} bytes")

    # Compress content based on type
    is_static_path = request.url.path.startswith(static_prefix)
    compressed_body = compress_content(request.url.path, response_body, is_static_path)
    
    # Log compression stats
    log_compression_stats(original_size, len(compressed_body))
    
    # Create new response with compressed content
    return create_compressed_response(response, compressed_body)


async def get_response_body(response: Response) -> bytes:
    """
    Extract the full response body from a FastAPI response.
    
    Args:
        response: The FastAPI response object
        
    Returns:
        Complete response body as bytes
    """
    response_body = b""
    async for chunk in response.body_iterator:  # type: ignore
        response_body += chunk
    return response_body


def compress_content(path: str, content: bytes, is_static: bool) -> bytes:
    """
    Compress content and optionally cache for static files.
    
    Args:
        path: The request path
        content: The content to compress
        is_static: Whether the content is static (to be cached)
        
    Returns:
        Compressed content bytes
    """
    if is_static:
        # キャッシュを利用して静的ファイルの圧縮処理を最適化
        logger.warning(f"Compressing static content for path: {path}")
        return get_compressed_content(path, content)
    else:
        # JSONレスポンスは毎回圧縮（キャッシュしない）
        logger.warning("Compressing JSON response (not cached)")
        return gzip.compress(content)


def create_compressed_response(original_response: Response, compressed_body: bytes) -> Response:
    """
    Create a new response with compressed content.
    
    Args:
        original_response: The original FastAPI response
        compressed_body: The compressed content bytes
        
    Returns:
        New response with compression headers
    """
    new_response = Response(
        content=compressed_body,
        status_code=original_response.status_code,
        headers=dict(original_response.headers),
        media_type=original_response.media_type
    )
    new_response.headers["Content-Encoding"] = "gzip"
    new_response.headers["Content-Length"] = str(len(compressed_body))
    logger.warning(f"Response prepared with gzip encoding, status: {new_response.status_code}")
    return new_response


def log_compression_stats(original_size: int, compressed_size: int) -> None:
    """
    Log compression statistics.
    
    Args:
        original_size: Original content size in bytes
        compressed_size: Compressed content size in bytes
    """
    compression_ratio = (1 - compressed_size / original_size) * 100 if original_size > 0 else 0
    logger.warning(f"Compressed size: {compressed_size} bytes, compression ratio: {compression_ratio:.2f}%")


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
    cache_hit = file_path in _compressed_content_cache
    logger.warning(f"Cache {'hit' if cache_hit else 'miss'} for path: {file_path}")

    if not cache_hit:
        original_size = len(content)
        compressed_content = gzip.compress(content)
        compressed_size = len(compressed_content)
        compression_ratio = (1 - compressed_size / original_size) * 100 if original_size > 0 else 0

        logger.warning(f"Newly compressed content - original: {original_size} bytes, compressed: {compressed_size} bytes, ratio: {compression_ratio:.2f}%")
        _compressed_content_cache[file_path] = compressed_content

    return _compressed_content_cache[file_path]


_compressed_content_cache: dict[str, bytes] = {}
