from dataclasses import dataclass
from typing import Literal, TypedDict, Tuple, Callable
import math


deg2rad = math.pi / 180
rad2deg = 180 / math.pi


class Angle:
    '''
    This class represents an angle.
    '''
    Unit = Literal['degree', 'radian']

    def __init__(self, radian: float) -> None:
        self._radian = radian

    @property
    def degree(self) -> float:
        return rad2deg * self._radian

    @property
    def radian(self) -> float:
        return self._radian

    @classmethod
    def from_degree(cls, degree: float) -> 'Angle':
        return cls(deg2rad * degree)

    @classmethod
    def from_radian(cls, radian: float) -> 'Angle':
        return cls(radian)

    @classmethod
    def converter(cls, unit: Unit) -> Tuple[Callable[[float], 'Angle'], Callable[['Angle'], float]]:
        if unit == 'degree':
            angle_input = cls.from_degree
            angle_output = _as_degree
        else:
            angle_input = cls.from_radian
            angle_output = _as_radian
        return angle_input, angle_output


def _as_degree(angle: Angle) -> float:
    return angle.degree


def _as_radian(angle: Angle) -> float:
    return angle.radian
