from dataclasses import dataclass
from typing import TYPE_CHECKING, Generic, NewType, TypeVar

import numpy
from pydantic import GetCoreSchemaHandler
from pydantic_core import CoreSchema, core_schema

from quicklook.utils.hash_utils import hash_iterable

CcdDataType = NewType('CcdDataType', str)


class VisitName(str):
    """Visit識別子。フォーマット: ``{repository_name}:{data_type}:{identifier}``"""

    def _parts(self) -> list[str]:
        parts = self.split(':')
        if len(parts) < 3:  # pragma: no cover
            raise ValueError(f'Invalid visit name: {self!r}  (expected format: repository_name:data_type:identifier)')
        return parts

    @property
    def repository_name(self) -> str:
        return self._parts()[0]

    @property
    def data_type(self) -> CcdDataType:
        return self._parts()[-2]  # type: ignore

    @property
    def name(self) -> str:
        return self._parts()[-1]

    @classmethod
    def __get_pydantic_core_schema__(cls, _src, _handler: GetCoreSchemaHandler) -> CoreSchema:
        return core_schema.no_info_after_validator_function(cls, core_schema.str_schema())


CcdName = NewType('CcdName', str)


@dataclass(frozen=True)
class CcdDataRef:
    visit: VisitName
    ccd: CcdName

    @property
    def fullname(self) -> str:
        return f"{self.visit}/{self.ccd}"

    def __str__(self) -> str:  # pragma: no cover
        return self.fullname


@dataclass
class Progress:
    total: int
    count: int = 0

    def update(self, count: int = 1):
        self.count += count
        return self

    def full(self):
        self.count = self.total
        return self

    def update_and_yield_every(self, every: int, *, count: int = 1):
        self.count += count
        if self.count % every == 0:
            yield self


T = TypeVar('T')


@dataclass
class ReturnValue(Generic[T]):
    value: T


@dataclass(frozen=True)
class TilePos:
    level: int
    i: int
    j: int

    def safe_hash(self) -> int:
        return hash_iterable((self.level, self.i, self.j))


@dataclass
class Tile:
    visit: VisitName
    pos: TilePos
    data: numpy.ndarray


@dataclass(frozen=True)
class PackedTilePos(TilePos):
    @classmethod
    def from_unpacked(cls, unpacked_pos: TilePos):
        from quicklook.config import config

        pack = config.tile_pack
        return cls(unpacked_pos.level, unpacked_pos.i >> pack, unpacked_pos.j >> pack)

    def unpackeds(self):
        from quicklook.config import config

        for i in range(1 << config.tile_pack):
            for j in range(1 << config.tile_pack):
                yield TilePos(self.level, self.i << config.tile_pack | i, self.j << config.tile_pack | j)

    def index(self, i: int, j: int) -> int:
        """
        Compute a unique index for a tile within this packed tile.

        Parameters:
        - i: Unpacked i-coordinate, range: [self.i << config.tile_pack, (self.i + 1) << config.tile_pack - 1]
        - j: Unpacked j-coordinate, range: [self.j << config.tile_pack, (self.j + 1) << config.tile_pack - 1]

        Returns:
        - A unique index in range [0, (1 << (2 * config.tile_pack)) - 1]
        """
        from quicklook.config import config

        local_i = i - (self.i << config.tile_pack)
        local_j = j - (self.j << config.tile_pack)

        # Ensure coordinates are within valid range
        if not (0 <= local_i < (1 << config.tile_pack) and 0 <= local_j < (1 << config.tile_pack)):  # pragma: no cover
            raise ValueError(
                f"Coordinates (i={i}, j={j}) outside range of packed tile (level={self.level}, i={self.i}, j={self.j})"
            )

        return (local_i << config.tile_pack) | local_j
