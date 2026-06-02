from collections.abc import Mapping
from dataclasses import dataclass
from typing import Generic, NewType, TypeVar

import numpy
from pydantic import GetCoreSchemaHandler
from pydantic_core import CoreSchema, core_schema

from quicklook.utils.hash_utils import hash_iterable

CcdDataType = NewType('CcdDataType', str)


def escape_visit_path_part(value: str) -> str:
    return value.replace('!', '!!').replace('/', '!-')


def unescape_visit_path_part(value: str) -> str:
    chars: list[str] = []
    i = 0
    while i < len(value):
        char = value[i]
        if char != '!':
            chars.append(char)
            i += 1
            continue
        if i + 1 >= len(value):
            raise ValueError(f'Invalid escaped value: {value!r}')
        next_char = value[i + 1]
        if next_char == '!':
            chars.append('!')
        elif next_char == '-':
            chars.append('/')
        else:
            raise ValueError(f'Invalid escaped value: {value!r}')
        i += 2
    return ''.join(chars)


def format_visit_dimensions(dimensions: Mapping[str, object]) -> str:
    return ','.join(f'{key}={dimensions[key]}' for key in sorted(dimensions))


def parse_visit_dimensions(dimensions_text: str) -> dict[str, str]:
    if not dimensions_text:
        raise ValueError('Visit dimensions must not be empty')
    parsed: dict[str, str] = {}
    for pair in dimensions_text.split(','):
        key, separator, value = pair.partition('=')
        if not separator or not key or not value:
            raise ValueError(f'Invalid dimension pair: {pair!r}')
        parsed[key] = value
    return parsed


def build_scope_id(repository_name: str, collection: str, dataset_type: str) -> str:
    return f'{repository_name}:{escape_visit_path_part(collection)}:{dataset_type}'


def parse_scope_id(scope_id: str) -> tuple[str, str, str]:
    repository_name, escaped_collection, dataset_type = scope_id.split(':', maxsplit=2)
    return repository_name, unescape_visit_path_part(escaped_collection), dataset_type


class VisitName(str):
    """Quicklook identifier.

    Canonical cache key:
    ``{repository}:{collection}:{dataset_type}:{key1=value1,key2=value2}``

    URL/path representation:
    ``{repository}:{escaped_collection}:{dataset_type}:{key1=value1,key2=value2}``
    """

    def __new__(cls, value: str):
        cls._parse(value)
        return super().__new__(cls, value)

    @staticmethod
    def _parse(value: str) -> tuple[str, str, str, dict[str, str], str]:
        parts = value.split(':')
        if len(parts) == 3 and parts[1] == 'by_uuid':
            return parts[0], 'by_uuid', 'by_uuid', {'uuid': parts[2]}, 'by_uuid'
        if len(parts) == 3:
            return parts[0], 'legacy', parts[1], {'legacy': parts[2]}, 'legacy'
        if len(parts) != 4:  # pragma: no cover
            raise ValueError(
                f'Invalid visit name: {value!r} '
                '(expected format: repository:collection:dataset_type:key=value[,key=value])'
            )
        repository_name, escaped_collection, dataset_type, dimensions_text = parts
        return (
            repository_name,
            unescape_visit_path_part(escaped_collection),
            dataset_type,
            parse_visit_dimensions(dimensions_text),
            'canonical',
        )

    @classmethod
    def from_cache_key(cls, cache_key: str) -> 'VisitName':
        parts = cache_key.split(':')
        if len(parts) == 3 and parts[1] == 'by_uuid':
            return cls(cache_key)
        if len(parts) != 4:
            raise ValueError(f'Invalid visit cache key: {cache_key!r}')
        repository_name, collection, dataset_type, dimensions_text = parts
        return cls(f'{repository_name}:{escape_visit_path_part(collection)}:{dataset_type}:{dimensions_text}')

    @classmethod
    def from_parts(
        cls,
        *,
        repository_name: str,
        collection: str,
        dataset_type: str,
        dimensions: Mapping[str, object],
    ) -> 'VisitName':
        return cls(
            f'{repository_name}:{escape_visit_path_part(collection)}:{dataset_type}:{format_visit_dimensions(dimensions)}'
        )

    @property
    def is_by_uuid(self) -> bool:
        return self._parse(self)[4] == 'by_uuid'

    @property
    def is_legacy(self) -> bool:
        return self._parse(self)[4] == 'legacy'

    @property
    def repository_name(self) -> str:
        return self._parse(self)[0]

    @property
    def collection(self) -> str:
        return self._parse(self)[1]

    @property
    def dataset_type(self) -> str:
        return self._parse(self)[2]

    @property
    def data_type(self) -> CcdDataType:
        return self.dataset_type  # type: ignore

    @property
    def dimensions(self) -> dict[str, str]:
        return self._parse(self)[3]

    @property
    def dimensions_text(self) -> str:
        return format_visit_dimensions(self.dimensions)

    @property
    def cache_key(self) -> str:
        if self.is_by_uuid or self.is_legacy:
            return str(self)
        return f'{self.repository_name}:{self.collection}:{self.dataset_type}:{self.dimensions_text}'

    @property
    def scope_id(self) -> str:
        if self.is_by_uuid:
            return f'{self.repository_name}:by_uuid'
        if self.is_legacy:
            return f'{self.repository_name}:{self.dataset_type}'
        return build_scope_id(self.repository_name, self.collection, self.dataset_type)

    @property
    def name(self) -> str:
        if self.is_by_uuid:
            return self.dimensions['uuid']
        if len(self.dimensions) != 1:
            raise ValueError(f'{self.cache_key} does not have a single quicklook dimension')
        return next(iter(self.dimensions.values()))

    @property
    def dimension_name(self) -> str:
        if self.is_by_uuid:
            return 'uuid'
        if len(self.dimensions) != 1:
            raise ValueError(f'{self.cache_key} does not have a single quicklook dimension')
        return next(iter(self.dimensions))

    @classmethod
    def __get_pydantic_core_schema__(cls, _src, _handler: GetCoreSchemaHandler) -> CoreSchema:
        return core_schema.no_info_after_validator_function(cls, core_schema.str_schema())


CcdName = NewType('CcdName', str)


@dataclass(frozen=True)
class CcdDataRef:
    visit: VisitName
    ccd: CcdName

    @property
    def fullname(self) -> str:
        return f"{self.visit}/{self.ccd}"

    def __str__(self) -> str:  # pragma: no cover
        return self.fullname


@dataclass
class Progress:
    total: int
    count: int = 0

    def update(self, count: int = 1):
        self.count += count
        return self

    def full(self):
        self.count = self.total
        return self

    def update_and_yield_every(self, every: int, *, count: int = 1):
        self.count += count
        if self.count % every == 0:
            yield self


T = TypeVar('T')


@dataclass
class ReturnValue(Generic[T]):
    value: T


@dataclass(frozen=True)
class TilePos:
    level: int
    i: int
    j: int

    def safe_hash(self) -> int:
        return hash_iterable((self.level, self.i, self.j))


@dataclass
class Tile:
    visit: VisitName
    pos: TilePos
    data: numpy.ndarray


@dataclass(frozen=True)
class PackedTilePos(TilePos):
    @classmethod
    def from_unpacked(cls, unpacked_pos: TilePos):
        from quicklook.config import config

        pack = config.tile_pack
        return cls(unpacked_pos.level, unpacked_pos.i >> pack, unpacked_pos.j >> pack)

    def unpackeds(self):
        from quicklook.config import config

        for i in range(1 << config.tile_pack):
            for j in range(1 << config.tile_pack):
                yield TilePos(self.level, self.i << config.tile_pack | i, self.j << config.tile_pack | j)

    def index(self, i: int, j: int) -> int:
        """
        Compute a unique index for a tile within this packed tile.

        Parameters:
        - i: Unpacked i-coordinate, range: [self.i << config.tile_pack, (self.i + 1) << config.tile_pack - 1]
        - j: Unpacked j-coordinate, range: [self.j << config.tile_pack, (self.j + 1) << config.tile_pack - 1]

        Returns:
        - A unique index in range [0, (1 << (2 * config.tile_pack)) - 1]
        """
        from quicklook.config import config

        local_i = i - (self.i << config.tile_pack)
        local_j = j - (self.j << config.tile_pack)

        if not (0 <= local_i < (1 << config.tile_pack) and 0 <= local_j < (1 << config.tile_pack)):  # pragma: no cover
            raise ValueError(
                f"Coordinates (i={i}, j={j}) outside range of packed tile (level={self.level}, i={self.i}, j={self.j})"
            )

        return (local_i << config.tile_pack) | local_j
