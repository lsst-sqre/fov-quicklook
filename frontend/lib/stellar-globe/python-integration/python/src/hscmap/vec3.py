import math
from dataclasses import dataclass
from typing import List, Tuple, TypedDict, Union

from .angle import Angle


class SkyCooerdDict(TypedDict):
    ''':meta private:'''

    ra: float
    dec: float


@dataclass
class SkyCoord:
    '''
    This class represents a position on the celestial sphere.
    The position is represented by right ascension and declination.
    '''

    ra: Angle
    dec: Angle

    def as_dict(self) -> SkyCooerdDict:
        ''':meta private:'''
        return {'ra': self.ra.radian, 'dec': self.dec.radian}

    def as_vec3(self) -> 'Vec3':
        '''
        Convert the position to a :class:`Vec3`.
        '''
        return Vec3(
            math.cos(self.ra.radian) * math.cos(self.dec.radian),
            math.sin(self.ra.radian) * math.cos(self.dec.radian),
            math.sin(self.dec.radian),
        )

    @classmethod
    def from_degree(cls, ra: float, dec: float) -> 'SkyCoord':
        return cls(Angle.from_degree(ra), Angle.from_degree(dec))

    @classmethod
    def from_radian(cls, ra: float, dec: float) -> 'SkyCoord':
        return cls(Angle.from_radian(ra), Angle.from_radian(dec))

    @classmethod
    def from_vec3(cls, vec: 'Vec3') -> 'SkyCoord':
        vec = vec.normalize()
        ra = math.atan2(vec.y, vec.x)
        dec = math.asin(vec.z)
        return cls(Angle.from_radian(ra), Angle.from_radian(dec))


@dataclass
class Vec3:
    '''
    This class represents a 3D vector.
    Operator overloading is implemented for addition, subtraction, multiplication, division, negation, and absolute value.

    ::

        a = Vec3(1, 2, 3)
        b = Vec3(4, 5, 6)
        c = a + b  # c = Vec3(5, 7, 9)
        d = a - b  # d = Vec3(-3, -3, -3)
        e = a * 2  # e = Vec3(2, 4, 6)
        f = 2 * a  # f = Vec3(2, 4, 6)
        g = a / 2  # g = Vec3(0.5, 1, 1.5)
        h = -a  # h = Vec3(-1, -2, -3)
        i = abs(a)  # i = 3.7416573867739413
    '''

    x: float
    y: float
    z: float

    def __add__(self, other: 'Vec3') -> 'Vec3':
        return Vec3(self.x + other.x, self.y + other.y, self.z + other.z)

    def __sub__(self, other: 'Vec3') -> 'Vec3':
        return Vec3(self.x - other.x, self.y - other.y, self.z - other.z)

    def __mul__(self, other: float) -> 'Vec3':
        return Vec3(self.x * other, self.y * other, self.z * other)

    def __rmul__(self, other: float) -> 'Vec3':
        return Vec3(self.x * other, self.y * other, self.z * other)

    def __truediv__(self, other: float) -> 'Vec3':
        return Vec3(self.x / other, self.y / other, self.z / other)

    def __neg__(self) -> 'Vec3':
        return Vec3(-self.x, -self.y, -self.z)

    def __abs__(self) -> float:
        return math.sqrt(self.x**2 + self.y**2 + self.z**2)

    def normalize(self) -> 'Vec3':
        '''
        Return a normalized vector.
        '''
        return self / abs(self)

    def dot(self, other: 'Vec3') -> float:
        '''
        Return the dot product of this vector and `other`.
        '''
        return self.x * other.x + self.y * other.y + self.z * other.z

    def cross(self, other: 'Vec3') -> 'Vec3':
        '''
        Return the cross product of this vector and `other`.
        '''
        return Vec3(
            self.y * other.z - self.z * other.y,
            self.z * other.x - self.x * other.z,
            self.x * other.y - self.y * other.x,
        )

    def angle(self, other: 'Vec3') -> Angle:
        '''
        Return the angle between this vector and `other`.
        '''
        return Angle(math.acos(self.dot(other) / (abs(self) * abs(other))))

    def as_tuple(self) -> Tuple[float, float, float]:
        return (self.x, self.y, self.z)

    def as_list(self) -> List[float]:
        return [self.x, self.y, self.z]


SkyCoordOrVec3 = Union[SkyCoord, Vec3]


def as_vec3(position: SkyCoordOrVec3):
    '''
    Convert `position` to a :class:`Vec3`.
    '''
    if isinstance(position, SkyCoord):
        return position.as_vec3()
    return position


def as_sky_coord(position: SkyCoordOrVec3):
    '''
    Convert `position` to a :class:`SkyCoord`.
    '''
    if isinstance(position, Vec3):
        return SkyCoord.from_vec3(position)
    return position
