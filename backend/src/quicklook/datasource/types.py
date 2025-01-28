import abc
from dataclasses import dataclass
from typing import Literal


DataType = Literal['raw', 'calexp']


@dataclass
class Query:
    data_type: DataType
    exposure: str | None = None
    day_obs: int | None = None
    limit: int = 1000


@dataclass
class Visit:
    exposure: str


class CcdRef(abc.ABC):
    @property
    @abc.abstractmethod
    def exposure(self) -> str: ...

    @property
    @abc.abstractmethod
    def ccd_name(self) -> str: ...


class DataSourceBase(abc.ABC):
    @abc.abstractmethod
    def query_datasets(self, q: Query) -> list[Visit]: ...

    @abc.abstractmethod
    def get_data(self, ref: CcdRef) -> bytes: ...
