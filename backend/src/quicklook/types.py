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
class GeneratorProgress:
    download: Progress
    preprocess: Progress
    maketile: Progress


@dataclass
class CcdMeta:
    ccd_id: CcdId
    image_stat: ImageStat
    amps: list[AmpMeta]
    bbox: BBox


@dataclass
class QuicklookMeta:
    ccd_meta: list[CcdMeta]


MessageFromGeneratorToCoordinator = None | GeneratorProgress | BaseException | CcdMeta
