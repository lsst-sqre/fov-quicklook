import pytest

import quicklook.object_storage as object_storage
from quicklook.object_storage import TileCacheMetadata, TileCacheMetadataError
from quicklook.utils.s3 import NoSuchKey


def test_put_tile_cache_metadata_sync_writes_json_payload(monkeypatch):
    calls = []

    def fake_put_object(key: str, value: bytes, content_type: str):
        calls.append((key, value, content_type))
        return len(value)

    monkeypatch.setattr(object_storage, 'put_object', fake_put_object)

    size = object_storage.put_tile_cache_metadata_sync(TileCacheMetadata(schema_version=7))

    assert size == len(calls[0][1])
    assert calls == [('meta.json', b'{"tile_cache_schema_version":7}', 'application/json')]


def test_get_tile_cache_metadata_sync_parses_valid_json(monkeypatch):
    monkeypatch.setattr(
        object_storage,
        'get_object',
        lambda key: b'{"tile_cache_schema_version":5}',
    )

    metadata = object_storage.get_tile_cache_metadata_sync()

    assert metadata == TileCacheMetadata(schema_version=5)


def test_get_tile_cache_metadata_sync_returns_none_when_metadata_is_missing(monkeypatch):
    def fake_get_object(key: str):
        raise NoSuchKey(key)

    monkeypatch.setattr(object_storage, 'get_object', fake_get_object)

    metadata = object_storage.get_tile_cache_metadata_sync()

    assert metadata is None


@pytest.mark.parametrize(
    'payload',
    [
        b'not-json',
        b'[]',
        b'{"tile_cache_schema_version":"1"}',
    ],
)
def test_get_tile_cache_metadata_sync_rejects_invalid_payload(monkeypatch, payload: bytes):
    monkeypatch.setattr(object_storage, 'get_object', lambda key: payload)

    with pytest.raises(TileCacheMetadataError):
        object_storage.get_tile_cache_metadata_sync()
