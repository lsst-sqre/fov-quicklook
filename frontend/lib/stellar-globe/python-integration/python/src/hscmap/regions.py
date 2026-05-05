from dataclasses import dataclass
from typing import List, Optional, Tuple, cast

from .angle import Angle
from .models.actions.regions.newCircularRegionAdded import Model as NewCircularRegionAdded
from .models.actions.regions.newLinearRegionAdded import Model as NewLinearRegionAdded
from .models.actions.regions.newPathRegionAdded import Model as NewPathRegionAdded
from .models.actions.regions.newRectangularRegionAdded import Model as NewRectangularRegionAdded
from .models.actions.regions.newTextRegionAdded import Model as NewTextRegionAdded
from .models.actions.regions.regionDeleted import Model as regionDeleted
from .models.actions.regions.regionsReordered import Model as RegionsReordered
from .models.actions.regions.regionUpdated import Model as RegionUpdated
from .models.store import CircularRegion as CircularRegionState
from .models.store import LinearRegion as LinearRegionState
from .models.store import Path
from .models.store import PathRegion as PathRegionState
from .models.store import RectangularRegion as RectangularRegionState
from .models.store import TextRegion as TextRegionState
from .shape import ShapeBase
from .tinyid import tinyid
from .vec3 import SkyCoord
from .window import Window


@dataclass
class RegionManager:
    _w: Window

    @property
    def members(self) -> List['RegionBase']:
        self._w.sync()
        return [type_map[cast(str, r['type'])](r['id'], self._w) for r in self._w._store_state['regions']['regions']]

    def new_text(self, *, position: Tuple[float, float], text: str, color: Optional[List[float]] = None):
        w = self._w
        id = tinyid()
        positionCoord = SkyCoord(w._angle_input(position[0]), w._angle_input(position[1]))
        action = NewTextRegionAdded(
            type='regions/newTextRegionAdded',
            payload={
                'color': color,
                'id': id,
                'name': text,
                'position': positionCoord.as_dict(),
                'showLabel': True,
                'type': 'Text',
                'visible': True,
            },
        )
        w._dispatch(action)
        return TextRegion(id, w)

    def new_circle(self, *, center: Tuple[float, float], radius: float, name='', color: Optional[List[float]] = None):
        w = self._w
        id = tinyid()
        centerCoord = SkyCoord(w._angle_input(center[0]), w._angle_input(center[1]))
        action = NewCircularRegionAdded(
            type='regions/newCircularRegionAdded',
            payload={
                'color': color,
                'name': name,
                'id': id,
                'center': centerCoord.as_dict(),
                'radius': w._angle_input(radius).radian,
                'showLabel': True,
                'type': 'Circular',
                'visible': True,
            },
        )
        w._dispatch(action)
        return CircleRegion(id, w)

    def new_line(self, *, start: Tuple[float, float], end: Tuple[float, float], name='', color: Optional[List[float]] = None):
        w = self._w
        id = tinyid()
        startCoord = SkyCoord(w._angle_input(start[0]), w._angle_input(start[1]))
        endCoord = SkyCoord(w._angle_input(end[0]), w._angle_input(end[1]))
        action = NewLinearRegionAdded(
            type='regions/newLinearRegionAdded',
            payload={
                'color': color,
                'id': id,
                'name': name,
                'start': startCoord.as_dict(),
                'end': endCoord.as_dict(),
                'showLabel': True,
                'type': 'Linear',
                'visible': True,
            },
        )
        w._dispatch(action)
        return LinearRegion(id, w)

    def new_rect(self, *, min_ra: float, max_ra: float, min_dec: float, max_dec: float, name='', color: Optional[List[float]] = None):
        w = self._w
        id = tinyid()
        action = NewRectangularRegionAdded(
            type='regions/newRectangularRegionAdded',
            payload={
                'color': color,
                'id': id,
                'name': name,
                'minRa': w._angle_input(min_ra).radian,
                'maxRa': w._angle_input(max_ra).radian,
                'minDec': w._angle_input(min_dec).radian,
                'maxDec': w._angle_input(max_dec).radian,
                'showLabel': True,
                'type': 'Rectangular',
                'visible': True,
            },
        )
        w._dispatch(action)
        return RectangularRegion(id, w)

    def from_shape(self, *, shape: ShapeBase, name=''):
        w = self._w
        id = tinyid()
        action = NewPathRegionAdded(
            type='regions/newPathRegionAdded',
            payload={
                'color': None,
                'id': id,
                'name': name,
                'paths': [path for path in shape.paths()],
                'showLabel': True,
                'type': 'Path',
                'visible': True,
            },
        )
        w._dispatch(action)
        return ShapeRegion(id, w)

    def clear(self):
        for r in self.members:
            r.delete()


@dataclass
class RegionBase:
    id: str
    _w: Window

    def _sync(self):
        self._w.sync()

    def _state(self):
        self._sync()
        for r in self._w._store_state['regions']['regions']:  # pragma: no branch
            if r['id'] == self.id:  # pragma: no branch
                return r
        raise ValueError(f"Region already deleted: {self.id}")  # pragma: no cover

    def _update(self, **updates):
        self._w._dispatch(
            RegionUpdated(
                type='regions/regionUpdated',
                payload={
                    'id': self.id,
                    'regionDef': {**self._state(), **updates},  # type: ignore
                },
            )
        )

    def surface(self):
        w = self._w
        ids = [r.id for r in w.regions.members]
        ids.remove(self.id)
        ids.append(self.id)
        w._dispatch(
            RegionsReordered(
                type='regions/regionsReordered',
                payload={'ids': ids},
            )
        )
        # TODO: Review react-stellar-globe
        # ↓Forced redraw. Without this, the display does not change even if the order of the regions changes.
        w.jump_to(*w.camera.center, duration=0.01)

    def delete(self):
        self._w._dispatch(
            regionDeleted(
                type='regions/regionDeleted',
                payload={'id': self.id},
            )
        )

    @property
    def visible(self) -> bool:
        return self._state()['visible']

    @visible.setter
    def visible(self, value: bool):
        self._update(visible=value)

    @property
    def show_label(self) -> bool:
        self._sync()
        return self._state()['showLabel']

    @show_label.setter
    def show_label(self, value: bool):
        self._update(showLabel=value)

    @property
    def name(self) -> str:
        self._sync()
        return self._state()['name']

    @name.setter
    def name(self, value: str):
        self._update(name=value)

    @property
    def color(self) -> List[float]:
        self._sync()
        return self._state()['color']

    @color.setter
    def color(self, value: List[float]):
        self._update(color=value)


class TextRegion(RegionBase):
    def _state(self) -> TextRegionState:
        return cast(TextRegionState, super()._state())

    @property
    def text(self) -> str:
        self._sync()
        return self._state()['name']

    @text.setter
    def text(self, value: str):
        self._update(name=value)

    @property
    def position(self) -> Tuple[float, float]:
        w = self._w
        self._sync()
        return (
            w._angle_output(Angle.from_radian(self._state()['position']['ra'])),
            w._angle_output(Angle.from_radian(self._state()['position']['dec'])),
        )

    @position.setter
    def position(self, value: Tuple[float, float]):
        w = self._w
        position = {
            'ra': w._angle_input(value[0]).radian,
            'dec': w._angle_input(value[1]).radian,
        }
        self._update(position=position)


class CircleRegion(RegionBase):
    def _state(self) -> CircularRegionState:
        return cast(CircularRegionState, super()._state())

    @property
    def center(self) -> Tuple[float, float]:
        w = self._w
        self._sync()
        return (
            w._angle_output(Angle.from_radian(self._state()['center']['ra'])),
            w._angle_output(Angle.from_radian(self._state()['center']['dec'])),
        )

    @center.setter
    def center(self, value: Tuple[float, float]):
        w = self._w
        center = {
            'ra': w._angle_input(value[0]).radian,
            'dec': w._angle_input(value[1]).radian,
        }
        self._update(center=center)

    @property
    def radius(self) -> float:
        self._sync()
        return self._w._angle_output(Angle.from_radian(self._state()['radius']))

    @radius.setter
    def radius(self, value: float):
        radius = self._w._angle_input(value).radian
        self._update(radius=radius)


class LinearRegion(RegionBase):
    def _state(self) -> LinearRegionState:
        return cast(LinearRegionState, super()._state())

    @property
    def start(self) -> Tuple[float, float]:
        w = self._w
        self._sync()
        return (
            w._angle_output(Angle.from_radian(self._state()['start']['ra'])),
            w._angle_output(Angle.from_radian(self._state()['start']['dec'])),
        )

    @start.setter
    def start(self, value: Tuple[float, float]):
        w = self._w
        start = {
            'ra': w._angle_input(value[0]).radian,
            'dec': w._angle_input(value[1]).radian,
        }
        self._update(start=start)

    @property
    def end(self) -> Tuple[float, float]:
        w = self._w
        self._sync()
        return (
            w._angle_output(Angle.from_radian(self._state()['end']['ra'])),
            w._angle_output(Angle.from_radian(self._state()['end']['dec'])),
        )

    @end.setter
    def end(self, value: Tuple[float, float]):
        w = self._w
        end = {
            'ra': w._angle_input(value[0]).radian,
            'dec': w._angle_input(value[1]).radian,
        }
        self._update(end=end)


class RectangularRegion(RegionBase):
    def _state(self) -> RectangularRegionState:
        return cast(RectangularRegionState, super()._state())

    @property
    def min_ra(self) -> float:
        return self._w._angle_output(Angle.from_radian(self._state()['minRa']))

    @min_ra.setter
    def min_ra(self, value: float):
        self._update(minRa=self._w._angle_input(value).radian)

    @property
    def max_ra(self) -> float:
        return self._w._angle_output(Angle.from_radian(self._state()['maxRa']))

    @max_ra.setter
    def max_ra(self, value: float):
        self._update(maxRa=self._w._angle_input(value).radian)

    @property
    def min_dec(self) -> float:
        return self._w._angle_output(Angle.from_radian(self._state()['minDec']))

    @min_dec.setter
    def min_dec(self, value: float):
        self._update(minDec=self._w._angle_input(value).radian)

    @property
    def max_dec(self) -> float:
        return self._w._angle_output(Angle.from_radian(self._state()['maxDec']))

    @max_dec.setter
    def max_dec(self, value: float):
        self._update(maxDec=self._w._angle_input(value).radian)


class ShapeRegion(RegionBase):
    def _state(self) -> PathRegionState:
        return cast(PathRegionState, super()._state())

    @property
    def paths(self) -> List[Path]:
        self._sync()
        return self._state()['paths']

    @paths.setter
    def paths(self, value: List[Path]):
        self._update(paths=value)


type_map = {
    'Text': TextRegion,
    'Circular': CircleRegion,
    'Linear': LinearRegion,
    'Rectangular': RectangularRegion,
    'Path': ShapeRegion,
}
