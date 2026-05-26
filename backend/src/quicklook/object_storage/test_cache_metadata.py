import quicklook.object_storage as object_storage
from quicklook.utils.s3 import S3Object


def test_put_object_writes_to_versioned_prefix(monkeypatch):
    calls = []

    def fake_put_object(key: str, value: bytes, content_type: str):
        calls.append((key, value, content_type))
        del key, value, content_type

    monkeypatch.setattr(object_storage.config, 's3_tile_key_prefix', 'cache-root')
    monkeypatch.setattr(object_storage, 's3_upload_object', lambda *_args: calls.append(_args))

    size = object_storage.put_object('quicklooks/repo:raw:4242/data.pickle', b'payload', cache_version=7)

    assert size == len(b'payload')
    assert calls == [
        (
            object_storage.config.s3_tile,
            'cache-root/v7/quicklooks/repo:raw:4242/data.pickle',
            b'payload',
            'application/octet-stream',
        )
    ]


def test_get_object_reads_from_current_version_prefix(monkeypatch):
    monkeypatch.setattr(object_storage.config, 's3_tile_key_prefix', '')
    monkeypatch.setattr(object_storage.config, 'tile_cache_schema_version', 3)
    monkeypatch.setattr(object_storage, 's3_download_object', lambda *_args: b'data')

    data = object_storage.get_object('quicklooks/repo:raw:4242/data.pickle')

    assert data == b'data'


def test_list_cache_versions_parses_version_directories(monkeypatch):
    monkeypatch.setattr(object_storage.config, 's3_tile_key_prefix', 'cache-root/')
    monkeypatch.setattr(
        object_storage,
        's3_list_objects',
        lambda *_args, **_kwargs: [
            S3Object(key='cache-root/v1/', type='directory', size=None),
            S3Object(key='cache-root/v9/', type='directory', size=None),
            S3Object(key='cache-root/not-a-version/', type='directory', size=None),
        ],
    )

    versions = object_storage.list_cache_versions()

    assert versions == {1, 9}


def test_delete_root_objects_by_prefix_uses_unversioned_root(monkeypatch):
    calls = []
    monkeypatch.setattr(object_storage.config, 's3_tile_key_prefix', 'cache-root')
    monkeypatch.setattr(object_storage, 's3_delete_objects_with_prefix', lambda *_args: calls.append(_args))

    object_storage.delete_root_objects_by_prefix('v2/')

    assert calls == [
        (
            object_storage.config.s3_tile,
            'cache-root/v2/',
        )
    ]
