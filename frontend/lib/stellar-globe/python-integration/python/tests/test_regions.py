import math
from hscmap.window import Window
from hscmap.comm.mock import MockCommOptions
from hscmap.regions import TextRegion, CircleRegion, LinearRegion, ShapeRegion, RectangularRegion, SkyCoord, Angle
import pytest


def test_regions(w: Window):
    w.regions


def test_regions_text(w: Window):
    t = w.regions.new_text(position=(0, 0), text="test", color=[1, 0, 0, 1])
    w.sync()
    assert isinstance(w.regions.members[0], TextRegion)

    t.color = [0, 1, 0, 1]
    assert t.color == [0, 1, 0, 1]

    assert t.visible
    t.visible = False
    assert t.visible is False

    assert t.show_label
    t.show_label = False
    assert t.show_label is False

    t.name = 'new name'
    assert t.name == 'new name'

    t.text = 'new text'
    assert t.text == 'new text'

    t.position = (1, 1)
    assert t.position == (1, 1)

    assert len(w.regions.members) == 1
    t.delete()
    assert len(w.regions.members) == 0


def test_regions_circle(w: Window):
    center = (0.0, 0.0)
    radius = 1.0
    color = [0.5, 0.5, 0.5, 1.0]
    name = "circle"
    c = w.regions.new_circle(name=name, center=center, radius=radius, color=color)
    assert isinstance(w.regions.members[0], CircleRegion)

    c.center = (1, 1)
    assert c.center == (1, 1)

    c.radius = 2
    assert c.radius == 2


def test_regions_line(w: Window):
    start = (0.0, 0.0)
    end = (1.0, 1.0)
    color = [0.5, 0.5, 0.5, 1.0]
    name = "line"
    l = w.regions.new_line(name=name, start=start, end=end, color=color)
    assert isinstance(w.regions.members[0], LinearRegion)

    l.start = (1, 1)
    assert l.start == (1, 1)

    l.end = (2, 2)
    assert l.end == (2, 2)


def test_regions_rect(w: Window):
    r = w.regions.new_rect(
        name="rect",
        min_dec=0,
        max_dec=1,
        min_ra=0,
        max_ra=1,
        color=[0.5, 0.5, 0.5, 1.0],
    )
    assert isinstance(w.regions.members[0], RectangularRegion)

    r.min_dec = 1
    r.max_dec = 2
    r.min_ra = 3
    r.max_ra = 4
    assert math.isclose(r.min_dec, 1)
    assert math.isclose(r.max_dec, 2)
    assert math.isclose(r.min_ra, 3)
    assert math.isclose(r.max_ra, 4)


def test_regions_polygon(w: Window):
    from hscmap.shape import Polygon

    p = w.regions.from_shape(shape=Polygon(center=SkyCoord.from_degree(0, 0), radius=Angle.from_degree(1), n=3))
    assert isinstance(w.regions.members[0], ShapeRegion)

    assert isinstance(p.paths, list)
    assert len(p.paths) == 1
    p.paths = []
    assert len(p.paths) == 0


def test_regions_clear(w: Window):
    w.regions.new_text(position=(0, 0), text="test", color=[1, 0, 0, 1])
    w.regions.clear()
    assert len(w.regions.members) == 0


def test_region_sufrace(w: Window):
    for i in range(3):
        w.regions.new_text(position=(0, i), text="test", color=[1, 0, 0, 1])
    w.sync()
    r = w.regions.members[0]
    assert w.regions.members[0].id != w.regions.members[-1].id
    r.surface()
    assert r.id == w.regions.members[-1].id

