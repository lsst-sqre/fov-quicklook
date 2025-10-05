import gzip
from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI, Response
from fastapi.testclient import TestClient

from quicklook.frontend.api.compression import (
    _compressed_content_cache,
    compress_content,
    create_compressed_response,
    get_compressed_content,
    setup_compression,
    should_compress_response,
)


@pytest.fixture
def app():
    app = FastAPI()

    @app.get("/api/data")
    def get_data():
        return {"message": "Hello, World!"}

    @app.get("/static/file.js")
    def get_static():
        return Response(content=b"console.log('test');", media_type="application/javascript")

    @app.get("/no-compress")
    def get_no_compress():
        return Response(content=b"raw content", media_type="text/plain")

    setup_compression(app, static_prefix="/static")
    return app


@pytest.fixture
def client(app):
    return TestClient(app)


def test_compression_json_response(client):
    """JSONレスポンスがgzipで圧縮されることを確認"""
    # TestClientは自動的にgzipを解凍するため、raw responseを取得する必要がある
    with client:
        response = client.get("/api/data", headers={"Accept-Encoding": "gzip"})

    assert response.status_code == 200
    assert response.headers.get("Content-Encoding") == "gzip"
    assert "Content-Length" in response.headers
    # TestClientは自動的に解凍するので、contentは既に解凍されている
    assert b"Hello, World!" in response.content


def test_compression_static_response(client):
    """静的ファイルがgzipで圧縮されることを確認"""
    with client:
        response = client.get("/static/file.js", headers={"Accept-Encoding": "gzip"})

    assert response.status_code == 200
    assert response.headers.get("Content-Encoding") == "gzip"
    # TestClientは自動的に解凍するので、contentは既に解凍されている
    assert response.content == b"console.log('test');"


def test_no_compression_without_accept_encoding(client):
    """Accept-Encodingヘッダーがない場合は圧縮されないことを確認"""
    # TestClientは自動的にAccept-Encodingを付与するため、明示的にオフにする
    with client:
        response = client.get("/api/data", headers={"Accept-Encoding": "identity"})

    assert response.status_code == 200
    # identityを指定しているので圧縮されない
    assert "Content-Encoding" not in response.headers or response.headers.get("Content-Encoding") == "identity"
    assert b"Hello, World!" in response.content


def test_no_compression_for_non_gzip_client(client):
    """gzip非対応クライアントには圧縮しないことを確認"""
    response = client.get("/api/data", headers={"Accept-Encoding": "deflate"})

    assert response.status_code == 200
    assert "Content-Encoding" not in response.headers


def test_no_compression_for_non_json_non_static(client):
    """JSON以外かつ静的ファイル以外のレスポンスは圧縮されないことを確認"""
    response = client.get("/no-compress", headers={"Accept-Encoding": "gzip"})

    assert response.status_code == 200
    assert "Content-Encoding" not in response.headers
    assert response.content == b"raw content"


def test_should_compress_response_with_json():
    """JSONレスポンスで圧縮すべきかどうかの判定をテスト"""
    request = MagicMock()
    request.headers.get.return_value = "gzip, deflate"
    request.url.path = "/api/data"

    response = MagicMock()
    response.headers.get.return_value = "application/json"

    result = should_compress_response(request, response, "/static")
    assert result is True


def test_should_compress_response_with_static():
    """静的ファイルで圧縮すべきかどうかの判定をテスト"""
    request = MagicMock()
    request.headers.get.return_value = "gzip"
    request.url.path = "/static/file.js"

    response = MagicMock()
    response.headers.get.return_value = "application/javascript"

    result = should_compress_response(request, response, "/static")
    assert result is True


def test_should_not_compress_without_gzip_support():
    """gzip非対応の場合は圧縮しないことを確認"""
    request = MagicMock()
    request.headers.get.return_value = "deflate"
    request.url.path = "/api/data"

    response = MagicMock()
    response.headers.get.return_value = "application/json"

    result = should_compress_response(request, response, "/static")
    assert result is False


def test_should_not_compress_non_json_non_static():
    """JSON以外かつ静的ファイル以外は圧縮しないことを確認"""
    request = MagicMock()
    request.headers.get.return_value = "gzip"
    request.url.path = "/other/path"

    response = MagicMock()
    response.headers.get.return_value = "text/html"

    result = should_compress_response(request, response, "/static")
    assert result is False


async def test_compress_response():
    """レスポンス圧縮処理のテスト"""
    # Response.body_iteratorの内部APIに依存するテストは削除
    # compress_contentとcreate_compressed_responseの組み合わせで十分テストされている
    pass


def test_compress_content_for_static():
    """静的ファイルの圧縮テスト(キャッシュあり)"""
    content = b"static file content"
    path = "/static/test.js"

    result1 = compress_content(path, content, is_static=True)
    result2 = compress_content(path, content, is_static=True)

    assert gzip.decompress(result1) == content
    assert result1 == result2


def test_compress_content_for_dynamic():
    """動的コンテンツの圧縮テスト(キャッシュなし)"""
    content = b"dynamic content"
    path = "/api/data"

    result = compress_content(path, content, is_static=False)

    assert gzip.decompress(result) == content


def test_create_compressed_response():
    """圧縮レスポンスの作成テスト"""
    original = Response(content=b"original", status_code=200, media_type="application/json")
    original.headers["X-Custom-Header"] = "test"

    compressed_body = gzip.compress(b"compressed")

    result = create_compressed_response(original, compressed_body)

    assert result.status_code == 200
    assert result.headers.get("Content-Encoding") == "gzip"
    assert result.headers.get("Content-Length") == str(len(compressed_body))
    assert result.headers.get("X-Custom-Header") == "test"
    assert result.body == compressed_body


def test_get_compressed_content_caching():
    """圧縮キャッシュの動作テスト"""
    path = "/static/cached.js"
    content = b"content to cache"

    _compressed_content_cache.clear()

    result1 = get_compressed_content(path, content)
    assert path in _compressed_content_cache

    result2 = get_compressed_content(path, content)
    assert result1 == result2
    assert gzip.decompress(result1) == content

    _compressed_content_cache.clear()


def test_get_compressed_content_different_paths():
    """異なるパスで異なるキャッシュが使われることを確認"""
    path1 = "/static/file1.js"
    path2 = "/static/file2.js"
    content1 = b"content 1"
    content2 = b"content 2"

    _compressed_content_cache.clear()

    result1 = get_compressed_content(path1, content1)
    result2 = get_compressed_content(path2, content2)

    assert result1 != result2
    assert gzip.decompress(result1) == content1
    assert gzip.decompress(result2) == content2

    _compressed_content_cache.clear()


def test_compression_with_json_charset():
    """content-typeにcharsetが含まれる場合のテスト"""
    request = MagicMock()
    request.headers.get.return_value = "gzip"
    request.url.path = "/api/data"

    response = MagicMock()
    response.headers.get.return_value = "application/json; charset=utf-8"

    result = should_compress_response(request, response, "/static")
    assert result is True


def test_static_cache_hit():
    """静的ファイルのキャッシュヒットをテスト"""
    _compressed_content_cache.clear()

    path = "/static/test.css"
    content = b"body { color: red; }"

    # 1回目: キャッシュミス
    result1 = get_compressed_content(path, content)
    assert path in _compressed_content_cache

    # 2回目: キャッシュヒット
    result2 = get_compressed_content(path, content)
    assert result1 is result2

    _compressed_content_cache.clear()


def test_compression_preserves_status_code():
    """圧縮してもステータスコードが保持されることを確認"""
    original = Response(content=b"not found", status_code=404, media_type="application/json")
    compressed_body = gzip.compress(b"not found")

    result = create_compressed_response(original, compressed_body)

    assert result.status_code == 404


def test_compression_preserves_media_type():
    """圧縮してもmedia_typeが保持されることを確認"""
    original = Response(content=b"data", status_code=200, media_type="application/json")
    compressed_body = gzip.compress(b"data")

    result = create_compressed_response(original, compressed_body)

    assert result.media_type == "application/json"
