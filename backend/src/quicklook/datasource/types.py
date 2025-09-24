import abc
from dataclasses import dataclass

from quicklook.types import CcdDataType, CcdId, Visit


@dataclass
class Query:
    data_type: CcdDataType
    limit: int
    exposure: int | None = None
    day_obs: int | None = None


class DataSourceBase(abc.ABC):
    @abc.abstractmethod
    def query_visits(self, q: Query) -> list[Visit]:  # pragma: no cover
        ...

    @abc.abstractmethod
    def list_ccds(self, visit: Visit) -> list[str]:  # pragma: no cover
        ...

    @abc.abstractmethod
    def get_data(self, ref: CcdId) -> bytes:  # pragma: no cover
        ...

    @abc.abstractmethod
    def get_metadata(self, ref: CcdId) -> 'DataSourceCcdMetadata':  # pragma: no cover
        ...

    @abc.abstractmethod
    def get_exposure_data_types(self, exposure: int) -> list[CcdDataType]: ...


@dataclass
class DataSourceCcdMetadata:
    visit: Visit
    ccd_name: str

    detector: int
    exposure: int
    day_obs: int
    uuid: str
