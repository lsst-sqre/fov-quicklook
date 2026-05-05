import math

from hscmap.vec3 import Angle, SkyCoord, Vec3, as_sky_coord, as_vec3


def test_addition():
    v1 = Vec3(1, 2, 3)
    v2 = Vec3(4, 5, 6)
    result = v1 + v2
    assert result == Vec3(5, 7, 9)


def test_subtraction():
    v1 = Vec3(1, 2, 3)
    v2 = Vec3(4, 5, 6)
    result = v1 - v2
    assert result == Vec3(-3, -3, -3)


def test_multiplication():
    v1 = Vec3(1, 2, 3)
    scalar = 2
    result = v1 * scalar
    assert result == Vec3(2, 4, 6)


def test_rmul():
    v1 = Vec3(1, 2, 3)
    scalar = 2
    result = scalar * v1
    assert result == Vec3(2, 4, 6)


def test_division():
    v1 = Vec3(1, 2, 3)
    scalar = 2
    result = v1 / scalar
    assert result == Vec3(0.5, 1, 1.5)


def test_negation():
    v1 = Vec3(1, 2, 3)
    result = -v1
    assert result == Vec3(-1, -2, -3)


def test_absolute_value():
    v1 = Vec3(3, 4, 0)
    result = abs(v1)
    assert result == 5.0


def test_normalize():
    v1 = Vec3(3, 4, 0)
    result = v1.normalize()
    assert math.isclose(result.x, 0.6)
    assert math.isclose(result.y, 0.8)
    assert math.isclose(result.z, 0.0)


def test_dot_product():
    v1 = Vec3(1, 2, 3)
    v2 = Vec3(4, 5, 6)
    result = v1.dot(v2)
    assert result == 32


def test_cross_product():
    v1 = Vec3(1, 2, 3)
    v2 = Vec3(4, 5, 6)
    result = v1.cross(v2)
    assert result == Vec3(-3, 6, -3)


def test_angle():
    v1 = Vec3(1, 0, 0)
    v2 = Vec3(0, 1, 0)
    result = v1.angle(v2)
    assert math.isclose(result.radian, math.pi / 2)


def test_as_tuple():
    v1 = Vec3(1, 2, 3)
    result = v1.as_tuple()
    assert result == (1, 2, 3)


def test_as_list():
    v1 = Vec3(1, 2, 3)
    result = v1.as_list()
    assert result == [1, 2, 3]


def test_skycoord():
    ra = Angle.from_degree(30)
    dec = Angle.from_degree(0)
    skycoord = SkyCoord(ra, dec)
    result = skycoord.as_dict()
    assert result == {'ra': math.pi / 6, 'dec': 0.0}
    v3 = skycoord.as_vec3()
    assert math.isclose(v3.x, math.sqrt(3) / 2)
    assert math.isclose(v3.y, 0.5)
    assert math.isclose(v3.z, 0.0)


def test_skycoord_from_degree():
    skycoord = SkyCoord.from_degree(30, 0)
    result = skycoord.as_dict()
    assert result == {'ra': math.pi / 6, 'dec': 0.0}


def test_skycoord_from_radian():
    skycoord = SkyCoord.from_radian(math.pi / 6, 0)
    result = skycoord.as_dict()
    assert result == {'ra': math.pi / 6, 'dec': 0.0}


def test_from_vec3():
    v1 = Vec3(1, 1, math.sqrt(2))
    result = SkyCoord.from_vec3(v1)
    assert math.isclose(result.ra.radian, math.pi / 4)
    assert math.isclose(result.dec.radian, math.pi / 4)


def test_as_sky_coord():
    v1 = Vec3(1, 1, 1)
    result = as_sky_coord(v1)
    assert isinstance(result, SkyCoord)
    assert math.isclose(result.ra.radian, math.pi / 4)
    assert math.isclose(result.dec.radian, math.atan2(1, math.sqrt(2)))


def test_as_sky_coord_with_skycoord():
    ra = Angle.from_degree(30)
    dec = Angle.from_degree(0)
    skycoord = SkyCoord(ra, dec)
    result = as_sky_coord(skycoord)
    assert isinstance(result, SkyCoord)
    assert result == skycoord


def test_as_vec3():
    ra = Angle.from_degree(30)
    dec = Angle.from_degree(0)
    skycoord = SkyCoord(ra, dec)
    result = as_vec3(skycoord)
    assert isinstance(result, Vec3)
    assert math.isclose(result.x, math.sqrt(3) / 2)
    assert math.isclose(result.y, 0.5)
    assert math.isclose(result.z, 0.0)


def test_as_vec3_with_vec3():
    v1 = Vec3(1, 1, 1)
    result = as_vec3(v1)
    assert isinstance(result, Vec3)
    assert result == v1
