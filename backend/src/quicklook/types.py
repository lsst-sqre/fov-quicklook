from dataclasses import dataclass
from functools import cache, cached_property
from typing import Literal, TypeAlias

import numpy

CcdDataType: TypeAlias = Literal['raw', 'post_isr_image', 'preliminary_visit_image']


@dataclass
class Progress:
    total: int
    count: int = 0

    def update(self, count: int = 1):
        self.count += count
        return self


@dataclass(frozen=True)
class Visit:
    # TODO: VisitIDという名前に変更
    # 1つの文字列で特定される
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


@dataclass(frozen=True)
class CcdId:
    visit: Visit
    ccd_name: str

    @cached_property
    def fullname(self):
        return f'{self.visit.id}/{self.ccd_name}'

    @cached_property
    def name(self):
        # TODO: メソッド名をfullnameに変更
        return self.fullname


@dataclass
class TilePos:
    level: int
    i: int
    j: int


@dataclass
class Tile:
    visit: Visit
    pos: TilePos
    data: numpy.ndarray
