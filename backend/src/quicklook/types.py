from pydantic import BaseModel
from dataclasses import dataclass
from functools import cache, cached_property
from typing import Any, Literal, TypeAlias

import numpy


CcdDataType: TypeAlias = Literal['raw', 'calexp']


@dataclass
class Progress:
    count: int
    total: int

    @staticmethod
    def noop_progress(_: 'Progress'):
        pass


# @dataclass
# class TileRange:
#     yi1: int
#     yi2: int
#     xi1: int
#     xi2: int


@dataclass
class BBox:
    miny: float
    maxy: float
    minx: float
    maxx: float

    def union(self, other: 'BBox'):
        return BBox(
            miny=min(self.miny, other.miny),
            maxy=max(self.maxy, other.maxy),
            minx=min(self.minx, other.minx),
            maxx=max(self.maxx, other.maxx),
        )


@dataclass(frozen=True)
class Visit:
    id: str  # '{data_type}:{exposure}'

    @cache
    def _parts(self):
        return self.id.split(':')

    @property
    def data_type(self):
        return self._parts()[-2]

    @property
    def name(self):
        return self._parts()[-1]

    @classmethod
    def from_id(cls, id: str):
        return cls(id)


@dataclass
class CcdId:
    visit: Visit
    ccd_name: str

    @cached_property
    def name(self):
        return f'{self.visit.id}/{self.ccd_name}'


@dataclass
class Tile:
    visit: Visit
    level: int
    i: int
    j: int
    data: numpy.ndarray


@dataclass
class ImageStat:
    median: float
    mad: float
    shape: tuple[int, ...]


@dataclass
class AmpMeta:
    amp_id: int
    bbox: BBox


type CardType = tuple[str, str, str, str]
type HeaderType = list[CardType]


@dataclass
class PreProcessedCcd:
    ccd_id: CcdId
    bbox: BBox
    pool: numpy.ndarray
    stat: ImageStat
    amps: list[AmpMeta]
    headers: list[HeaderType]


@dataclass(frozen=True)
class GeneratorPod:
    host: str
    port: int

    @cached_property
    def name(self):
        return f'{self.host}:{self.port}'

    Name = str


@dataclass
class GenerateProgress:
    download: Progress
    preprocess: Progress
    maketile: Progress


@dataclass
class MergeProgress:
    merge: Progress


@dataclass
class TransferProgress:
    transfer: Progress


@dataclass
class CcdMeta:
    ccd_id: CcdId
    image_stat: ImageStat
    amps: list[AmpMeta]
    bbox: BBox


class QuicklookMeta(BaseModel):
    ccd_meta: list[CcdMeta]


GenerateTaskResponse = None | GenerateProgress | BaseException | CcdMeta
MergeTaskResponse = None | MergeProgress | BaseException
TransferTaskResponse = None | TransferProgress | BaseException


@dataclass(frozen=True)
class TileId:
    level: int
    i: int
    j: int


@dataclass(frozen=True)
class PackedTileId:
    level: int
    i: int
    j: int

    @classmethod
    def from_unpacked(cls, level: int, i: int, j: int):
        from quicklook.config import config

        pack = config.tile_pack
        return cls(level, i >> pack, j >> pack)

    def unpackeds(self):
        from quicklook.config import config
        for i in range(1 << config.tile_pack):
            for j in range(1 << config.tile_pack):
                yield TileId(self.level, self.i << config.tile_pack | i, self.j << config.tile_pack | j)

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
        if not (0 <= local_i < (1 << config.tile_pack) and 0 <= local_j < (1 << config.tile_pack)):
            raise ValueError(f"Coordinates (i={i}, j={j}) outside range of packed tile (level={self.level}, i={self.i}, j={self.j})")
        
        return (local_i << config.tile_pack) | local_j
