import abc
import dataclasses
import math
from typing import Iterable, List

from .angle import Angle
from .models.actions.regions.newPathRegionAdded import Path, Point
from .vec3 import SkyCoordOrVec3, Vec3, as_vec3


class ShapeBase(abc.ABC):
    @abc.abstractmethod
    def paths(self) -> Iterable[Path]: ...  # pragma: no cover


@dataclasses.dataclass
class ShapeList(ShapeBase):
    shapes: List[ShapeBase]

    def paths(self) -> Iterable[Path]:
        for shape in self.shapes:
            yield from shape.paths()


@dataclasses.dataclass
class Polyline(ShapeBase):
    points: List[SkyCoordOrVec3]
    color: List[float]
    close: bool = False

    def paths(self) -> Iterable[Path]:
        yield Path(
            close=self.close,
            joint='NONE',
            points=[
                {
                    'color': self.color,
                    'position': as_vec3(p).as_list(),
                    'size': 0,
                }
                for p in self.points
            ],
        )


@dataclasses.dataclass
class Polygon(ShapeBase):
    center: SkyCoordOrVec3
    radius: Angle
    n: int
    offset: float = 0
    up: Vec3 = dataclasses.field(default_factory=lambda: Vec3(0, 0, 1))
    color: List[float] = dataclasses.field(default_factory=lambda: [0.5, 0.5, 0.5, 1.0])

    def paths(self) -> Iterable[Path]:
        n = self.n
        o = as_vec3(self.center)
        e2 = o.cross(self.up).normalize()
        e1 = e2.cross(o).normalize()
        r = self.radius.radian
        color = self.color
        yield from Polyline(
            points=[o + r * math.cos(2 * math.pi * i / n + self.offset) * e1 + r * math.sin(2 * math.pi * i / n + self.offset) * e2 for i in range(n)],
            color=color,
            close=True,
        ).paths()


@dataclasses.dataclass
class Grid(ShapeBase):
    center: SkyCoordOrVec3
    width: Angle
    height: Angle
    div_x: int
    div_y: int
    color: List[float]
    up: Vec3 = dataclasses.field(default_factory=lambda: Vec3(0, 0, 1))

    def paths(self) -> Iterable[Path]:
        o = as_vec3(self.center)
        e0 = self.up
        e1 = o.cross(e0).normalize()
        e2 = o.cross(e1).normalize()
        div_x = self.div_x
        div_y = self.div_y
        width = self.width.radian
        height = self.height.radian
        for i in range(div_y + 1):
            y = (i - div_y / 2) / div_y
            y1 = -0.5
            x2 = +0.5
            p1 = o + (width * y1 * e1) + (height * y * e2)
            p2 = o + (width * x2 * e1) + (height * y * e2)
            yield from Line(p1, p2, self.color).paths()
        for j in range(div_x + 1):
            x = (j - div_x / 2) / div_x
            y1 = -0.5
            y2 = +0.5
            p1 = o + (width * x * e1) + (height * y1 * e2)
            p2 = o + (width * x * e1) + (height * y2 * e2)
            yield from Line(p1, p2, self.color).paths()

    def cell_center_vecs(self):
        o = as_vec3(self.center)
        e0 = self.up
        e1 = o.cross(e0).normalize()
        e2 = o.cross(e1).normalize()
        div_x = self.div_x
        div_y = self.div_y
        width = self.width.radian
        height = self.height.radian
        for i in range(div_y):
            y = ((i + 0.5) - div_y / 2) / div_y
            for j in range(div_x):
                x = ((j + 0.5) - div_x / 2) / div_x
                yield o + (width * x * e1) + (height * y * e2)


@dataclasses.dataclass
class Line(ShapeBase):
    start: SkyCoordOrVec3
    end: SkyCoordOrVec3
    color: List[float]

    def paths(self) -> Iterable[Path]:
        return [
            Path(
                close=False,
                joint='NONE',
                points=[
                    {
                        'color': self.color,
                        'position': as_vec3(self.start).as_list(),
                        'size': 0,
                    },
                    {
                        'color': self.color,
                        'position': as_vec3(self.end).as_list(),
                        'size': 0,
                    },
                ],
            ),
        ]
