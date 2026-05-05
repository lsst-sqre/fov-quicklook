import math
from hscmap.angle import Angle


def test_degree_conversion():
    angle = Angle.from_degree(90)
    assert math.isclose(angle.degree, 90)
    assert math.isclose(angle.radian, math.pi / 2)


def test_radian_conversion():
    angle = Angle.from_radian(math.pi / 2)
    assert math.isclose(angle.degree, 90)
    assert math.isclose(angle.radian, math.pi / 2)


def test_converter_degree_to_radian():
    angle_input, angle_output = Angle.converter('degree')
    angle = angle_input(90)
    assert math.isclose(angle_output(angle), 90)
    assert math.isclose(angle.degree, 90)


def test_converter_radian_to_degree():
    angle_input, angle_output = Angle.converter('radian')
    angle = angle_input(math.pi / 2)
    assert math.isclose(angle_output(angle), math.pi / 2)
    assert math.isclose(angle.radian, math.pi / 2)
