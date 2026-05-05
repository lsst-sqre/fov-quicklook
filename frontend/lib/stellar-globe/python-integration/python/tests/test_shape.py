from hscmap import Window, Vec3, Angle
from hscmap.regions import ShapeRegion
from hscmap.shape import Grid, Line, ShapeList


def test_shape_grid(w: Window):
    div_x = 6
    div_y = 2
    grid = Grid(
        center=Vec3(1, 1, 1),
        color=[1, 1, 1, 1],
        div_x=div_x,
        div_y=div_y,
        height=Angle.from_degree(0.75),
        width=Angle.from_degree(1),
    )
    w.regions.from_shape(shape=grid)
    w.sync()
    shape: ShapeRegion = w.regions.members[-1]  # type: ignore
    assert len(shape.paths) == (div_y + 1) + (div_x + 1)


def test_shape_list(w: Window):
    l = ShapeList(
        [
            Line(color=[1, 1, 1, 1], start=Vec3(1, 1, 1), end=Vec3(2, 2, 2)),
            Line(color=[1, 1, 1, 1], start=Vec3(2, 2, 2), end=Vec3(3, 3, 3)),
        ]
    )
    w.regions.from_shape(shape=l)
    w.sync()
    shape: ShapeRegion = w.regions.members[-1]  # type: ignore
    assert len(shape.paths) == 2
