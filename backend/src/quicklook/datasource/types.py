import abc
from dataclasses import dataclass

from quicklook.types import CcdDataType, CcdId


@dataclass
class Query:
    data_type: CcdDataType
    exposure: str | None = None
    day_obs: int | None = None
    limit: int = 1000


@dataclass
class DataSourceVisit:
    data_type: CcdDataType
    exposure: str


class DataSourceBase(abc.ABC):
    @abc.abstractmethod
    def query_datasets(self, q: Query) -> list[DataSourceVisit]: ...

    @abc.abstractmethod
    def get_data(self, ref: CcdId) -> bytes: ...
