import pickle
from dataclasses import dataclass
from functools import lru_cache

from quicklook.config import config
from quicklook.types import PackedTilePos, TilePos, VisitName
from quicklook.utils.s3 import s3_download_object, s3_upload_object


def put(key: str, value: bytes) -> int:
    s3_upload_object(config.s3_tile, f'{config.s3_tile_key_prefix}{key}', value, 'application/octet-stream')
    return len(value)


def get(key: str) -> bytes:
    return s3_download_object(config.s3_tile, f'{config.s3_tile_key_prefix}{key}')


@dataclass
class VisitObjectStorage:
    visit: VisitName

    @classmethod
    def from_visit(cls, visit: VisitName) -> 'VisitObjectStorage':
        return cls(visit=visit)

    def _packed_tile_key(self, packed_pos: PackedTilePos) -> str:
        return f'packed-tile/{packed_pos.level}/{packed_pos.i}/{packed_pos.j}.npy.zstd.list.pickle'

    def put_packed_tile_array(self, packed_pos: PackedTilePos, array: list[bytes | None]) -> int:
        data = pickle.dumps(array)
        return self._put(self._packed_tile_key(packed_pos), data)

    @lru_cache(maxsize=32)  # Tile 100KB~200KBほど。config.tile_pack == 2 で PackedTile 1.6~3.2MBほど
    def get_packed_tile_array(self, packed_pos: PackedTilePos) -> list[bytes | None]:
        return pickle.loads(self._get(self._packed_tile_key(packed_pos)))

    def get_quicklook_tile_bytes(self, pos: TilePos) -> bytes | None:
        packed_pos = PackedTilePos.from_unpacked(pos)
        packed = self.get_packed_tile_array(packed_pos)
        index = packed_pos.index(packed_pos.i, packed_pos.j)
        return packed[index]

    def _put(self, key: str, value: bytes) -> int:
        return put(f'quicklooks/{self.visit}/{key}', value)

    def _get(self, key: str) -> bytes:
        return get(f'quicklooks/{self.visit}/{key}')
