import asyncio
import pickle
from dataclasses import dataclass
from functools import lru_cache
from typing import TYPE_CHECKING, Iterable, Literal

from quicklook.config import config
from quicklook.types import PackedTilePos, TilePos, VisitName

if TYPE_CHECKING:
    from quicklook.generator.generate_single_fits_tiles import CcdMetadata

from quicklook.utils.fitsheader import HeaderType
from quicklook.utils.s3 import (
    s3_delete_object,
    s3_delete_objects_with_prefix,
    s3_download_object,
    s3_list_objects,
    s3_upload_object,
)


def put_object(key: str, value: bytes) -> int:
    s3_upload_object(config.s3_tile, f'{config.s3_tile_key_prefix}{key}', value, 'application/octet-stream')
    return len(value)


def get_object(key: str) -> bytes:
    return s3_download_object(config.s3_tile, f'{config.s3_tile_key_prefix}{key}')


@dataclass
class Entry:
    name: str
    type: Literal['directory', 'file']
    size: int | None


def list_entries(prefix: str) -> Iterable[Entry]:
    for obj in s3_list_objects(config.s3_tile, prefix=f'{config.s3_tile_key_prefix}{prefix}'):
        if obj.type == 'file':
            yield Entry(name=obj.key.split('/')[-1], type=obj.type, size=obj.size)
        elif obj.type == 'directory':
            yield Entry(name=f'{obj.key.split('/')[-2]}/', type=obj.type, size=None)


def delete_object(key: str) -> None:
    s3_delete_object(config.s3_tile, f'{config.s3_tile_key_prefix}{key}')


def delete_objects_by_prefix(prefix: str) -> None:
    s3_delete_objects_with_prefix(config.s3_tile, f'{config.s3_tile_key_prefix}{prefix}')


@dataclass
class VisitObjectStorage:
    visit: VisitName

    @classmethod
    def from_visit(cls, visit: VisitName) -> 'VisitObjectStorage':
        return cls(visit=visit)

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
        index = packed_pos.index(packed_pos.i, packed_pos.j)
        return packed[index]

    def _put_sync(self, key: str, value: bytes) -> int:
        return put_object(f'quicklooks/{self.visit}/{key}', value)

    def _get_sync(self, key: str) -> bytes:
        return get_object(f'quicklooks/{self.visit}/{key}')

    def delete_all_sync(self) -> None:
        """このvisitに関連するすべてのオブジェクトを削除"""
        delete_objects_by_prefix(f'quicklooks/{self.visit}/')

    def put_fits_headers_sync(self, ccd_name: str, headers: list[HeaderType]) -> int:
        """FITS headerをobject storageに保存"""

        data = pickle.dumps(headers)
        return self._put_sync(f'fits-headers/{ccd_name}.pickle', data)

    def put_ccd_metadata_list_sync(self, metadata_list: list['CcdMetadata']) -> int:
        """CCD metadata listをobject storageに保存"""

        data = pickle.dumps(metadata_list)
        return self._put_sync('ccd-metadata-list.pickle', data)

    def get_ccd_metadata_list_sync(self) -> list['CcdMetadata']:
        data = self._get_sync('ccd-metadata-list.pickle')
        return pickle.loads(data)

    # Async versions (run sync versions in thread pool)
    async def put_packed_tile_array(self, packed_pos: PackedTilePos, array: list[bytes | None]) -> int:
        return await asyncio.to_thread(self.put_packed_tile_array_sync, packed_pos, array)

    async def get_packed_tile_array(self, packed_pos: PackedTilePos) -> list[bytes | None]:
        return await asyncio.to_thread(self.get_packed_tile_array_sync, packed_pos)

    async def get_quicklook_tile_bytes(self, pos: TilePos) -> bytes | None:
        return await asyncio.to_thread(self.get_quicklook_tile_bytes_sync, pos)

    async def delete_all(self) -> None:
        await asyncio.to_thread(self.delete_all_sync)

    async def put_fits_headers(self, ccd_name: str, headers: list[HeaderType]) -> int:
        return await asyncio.to_thread(self.put_fits_headers_sync, ccd_name, headers)

    async def put_ccd_metadata_list(self, metadata_list: list['CcdMetadata']) -> int:
        return await asyncio.to_thread(self.put_ccd_metadata_list_sync, metadata_list)

    async def get_ccd_metadata_list(self) -> list['CcdMetadata']:
        return await asyncio.to_thread(self.get_ccd_metadata_list_sync)
