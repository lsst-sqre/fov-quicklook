import abc
from dataclasses import dataclass

from quicklook.types import CcdDataType, CcdId, Visit


@dataclass
class Query:
    data_type: CcdDataType
    exposure: str | None = None
    day_obs: int | None = None
    limit: int = 1000


class DataSourceBase(abc.ABC):
    @abc.abstractmethod
    def query_visits(self, q: Query) -> list[Visit]: ...

    @abc.abstractmethod
    def list_ccds(self, visit: Visit) -> list[str]: ...

    @abc.abstractmethod
    def get_data(self, ref: CcdId) -> bytes: ...
