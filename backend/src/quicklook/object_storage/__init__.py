import asyncio
import json
import pickle
import re
from dataclasses import dataclass
from functools import lru_cache
from typing import TYPE_CHECKING, Iterable, Literal

from quicklook.config import config
from quicklook.types import CcdName, PackedTilePos, TilePos, VisitName
from quicklook.utils.async_wrap import async_wrap

if TYPE_CHECKING:
    from quicklook.generator.generate_single_fits_tiles import CcdMetadata

from quicklook.utils.fitsheader import HeaderType
from quicklook.utils.s3 import (
    NoSuchKey,
    s3_delete_object,
    s3_delete_objects_with_prefix,
    s3_download_object,
    s3_list_objects,
    s3_upload_object,
)

TILE_CACHE_METADATA_KEY = 'meta.json'
_CACHE_VERSION_DIRECTORY_PATTERN = re.compile(r'^v(?P<version>\d+)$')


class TileCacheMetadataError(ValueError):
    pass


@dataclass(frozen=True)
class TileCacheMetadata:
    schema_version: int


def current_cache_version() -> int:
    return config.tile_cache_schema_version


def _normalized_root_prefix() -> str:
    prefix = config.s3_tile_key_prefix
    if prefix and not prefix.endswith('/'):
        return f'{prefix}/'
    return prefix


def cache_version_prefix(cache_version: int) -> str:
    return f'{_normalized_root_prefix()}v{cache_version}/'


def _root_key(key: str) -> str:
    return f'{_normalized_root_prefix()}{key}'


def _versioned_key(key: str, cache_version: int | None = None) -> str:
    version = current_cache_version() if cache_version is None else cache_version
    return f'{cache_version_prefix(version)}{key}'


def put_object(
    key: str,
    value: bytes,
    content_type: str = 'application/octet-stream',
    *,
    cache_version: int | None = None,
) -> int:
    s3_upload_object(config.s3_tile, _versioned_key(key, cache_version), value, content_type)
    return len(value)


def get_object(key: str, *, cache_version: int | None = None) -> bytes:
    return s3_download_object(config.s3_tile, _versioned_key(key, cache_version))


def put_tile_cache_metadata_sync(metadata: TileCacheMetadata) -> int:
    payload = json.dumps(
        {'tile_cache_schema_version': metadata.schema_version},
        separators=(',', ':'),
        sort_keys=True,
    ).encode('utf-8')
    s3_upload_object(config.s3_tile, _root_key(TILE_CACHE_METADATA_KEY), payload, 'application/json')
    return len(payload)


def get_tile_cache_metadata_sync() -> TileCacheMetadata | None:
    try:
        payload = s3_download_object(config.s3_tile, _root_key(TILE_CACHE_METADATA_KEY))
    except NoSuchKey:
        return None

    try:
        parsed = json.loads(payload.decode('utf-8'))
    except (UnicodeDecodeError, json.JSONDecodeError) as e:
        raise TileCacheMetadataError('tile cache metadata is not valid UTF-8 JSON') from e

    if not isinstance(parsed, dict):
        raise TileCacheMetadataError('tile cache metadata must be a JSON object')

    schema_version = parsed.get('tile_cache_schema_version')
    if type(schema_version) is not int:
        raise TileCacheMetadataError('tile cache metadata must include integer tile_cache_schema_version')

    return TileCacheMetadata(schema_version=schema_version)


def list_cache_versions() -> set[int]:
    root_prefix = _normalized_root_prefix()
    versions: set[int] = set()
    for obj in s3_list_objects(config.s3_tile, prefix=root_prefix, delimiter='/'):
        if obj.type != 'directory':
            continue

        relative = obj.key.removeprefix(root_prefix).rstrip('/')
        match = _CACHE_VERSION_DIRECTORY_PATTERN.fullmatch(relative)
        if match is None:
            continue
        versions.add(int(match.group('version')))
    return versions


@dataclass
class Entry:
    name: str
    type: Literal['directory', 'file']
    size: int | None


def list_entries(prefix: str, *, cache_version: int | None = None) -> Iterable[Entry]:
    for obj in s3_list_objects(config.s3_tile, prefix=_versioned_key(prefix, cache_version)):
        if obj.type == 'file':
            yield Entry(name=obj.key.split('/')[-1], type=obj.type, size=obj.size)
        elif obj.type == 'directory':
            yield Entry(name=f'{obj.key.split('/')[-2]}/', type=obj.type, size=None)


def delete_object(key: str, *, cache_version: int | None = None) -> None:
    s3_delete_object(config.s3_tile, _versioned_key(key, cache_version))


def delete_objects_by_prefix(prefix: str, *, cache_version: int | None = None) -> None:
    s3_delete_objects_with_prefix(config.s3_tile, _versioned_key(prefix, cache_version))


def delete_root_objects_by_prefix(prefix: str = '') -> None:
    s3_delete_objects_with_prefix(config.s3_tile, _root_key(prefix))


def delete_cache_version(cache_version: int) -> None:
    delete_root_objects_by_prefix(f'v{cache_version}/')


@dataclass(frozen=True)
class VisitObjectStorage:
    visit: VisitName
    cache_version: int

    @classmethod
    def from_visit(cls, visit: VisitName, cache_version: int | None = None) -> 'VisitObjectStorage':
        return cls(visit=visit, cache_version=current_cache_version() if cache_version is None else cache_version)

    def _packed_tile_key(self, packed_pos: PackedTilePos) -> str:
        return f'packed-tile/{packed_pos.level}/{packed_pos.i}/{packed_pos.j}.npy.zstd.list.pickle'

    def put_packed_tile_array_sync(self, packed_pos: PackedTilePos, array: list[bytes | None]) -> int:
        data = pickle.dumps(array)
        return self._put_sync(self._packed_tile_key(packed_pos), data)

    @lru_cache(maxsize=32)  # Tile 100KB~200KBほど。config.tile_pack == 2 で PackedTile 1.6~3.2MBほど
    def get_packed_tile_array_sync(self, packed_pos: PackedTilePos) -> list[bytes | None]:
        return pickle.loads(self._get_sync(self._packed_tile_key(packed_pos)))

    def get_quicklook_tile_bytes_sync(self, pos: TilePos) -> bytes | None:
        packed_pos = PackedTilePos.from_unpacked(pos)
        packed = self.get_packed_tile_array_sync(packed_pos)
        index = packed_pos.index(pos.i, pos.j)
        return packed[index]

    def _put_sync(self, key: str, value: bytes) -> int:
        return put_object(f'quicklooks/{self.visit.cache_key}/{key}', value, cache_version=self.cache_version)

    def _get_sync(self, key: str) -> bytes:
        return get_object(f'quicklooks/{self.visit.cache_key}/{key}', cache_version=self.cache_version)

    def delete_all_sync(self) -> None:
        """このvisitに関連するすべてのオブジェクトを削除"""
        delete_objects_by_prefix(f'quicklooks/{self.visit.cache_key}/', cache_version=self.cache_version)

    def put_fits_headers_sync(self, ccd_name: CcdName, headers: list[HeaderType]) -> int:
        """FITS headerをobject storageに保存"""

        data = pickle.dumps(headers)
        return self._put_sync(f'fits-headers/{ccd_name}.pickle', data)

    def get_fits_headers_sync(self, ccd_name: CcdName) -> list[HeaderType]:
        """FITS headerをobject storageから取得"""

        data = self._get_sync(f'fits-headers/{ccd_name}.pickle')
        return pickle.loads(data)

    def put_ccd_metadata_list_sync(self, metadata_list: list['CcdMetadata']) -> int:
        """CCD metadata listをobject storageに保存"""

        data = pickle.dumps(metadata_list)
        return self._put_sync('ccd-metadata-list.pickle', data)

    def get_ccd_metadata_list_sync(self) -> list['CcdMetadata']:
        data = self._get_sync('ccd-metadata-list.pickle')
        return pickle.loads(data)

    def put_time_profile_sync(self, profile_data: dict) -> int:
        """time profileをobject storageに保存"""
        data = pickle.dumps(profile_data)
        return self._put_sync('time-profile.pickle', data)

    def get_time_profile_sync(self) -> dict:
        """time profileをobject storageから取得"""
        data = self._get_sync('time-profile.pickle')
        return pickle.loads(data)

    # Async versions (auto-generated from sync methods)
    put_packed_tile_array = async_wrap(put_packed_tile_array_sync)
    get_packed_tile_array = async_wrap(get_packed_tile_array_sync)
    get_quicklook_tile_bytes = async_wrap(get_quicklook_tile_bytes_sync)
    delete_all = async_wrap(delete_all_sync)
    put_fits_headers = async_wrap(put_fits_headers_sync)
    get_fits_headers = async_wrap(get_fits_headers_sync)
    put_ccd_metadata_list = async_wrap(put_ccd_metadata_list_sync)
    get_ccd_metadata_list = async_wrap(get_ccd_metadata_list_sync)
    put_time_profile = async_wrap(put_time_profile_sync)
    get_time_profile = async_wrap(get_time_profile_sync)


def clear_visit_object_storage_caches() -> None:
    VisitObjectStorage.get_packed_tile_array_sync.cache_clear()


async def put_tile_cache_metadata(metadata: TileCacheMetadata) -> int:
    return await asyncio.to_thread(put_tile_cache_metadata_sync, metadata)


async def get_tile_cache_metadata() -> TileCacheMetadata | None:
    return await asyncio.to_thread(get_tile_cache_metadata_sync)
