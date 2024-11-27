from dataclasses import dataclass
from functools import cached_property
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
    data_type: CcdDataType
    name: str

    @cached_property
    def id(self):
        return f'{self.data_type}:{self.name}'

    @classmethod
    def from_id(cls, id: str):
        data_type, name = id.split(':')
        return cls(data_type, name)  # type: ignore


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
class ProcessCcdResult:
    ccd_id: CcdId
    image_stat: ImageStat
    amps: list[AmpMeta]
    bbox: BBox


MessageFromGeneratorToCoordinator = None | GeneratorProgress | BaseException | ProcessCcdResult
