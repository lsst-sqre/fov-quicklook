import abc
from dataclasses import dataclass

from quicklook.types import CcdDataType, CcdId, Visit


@dataclass
class Query:
    data_type: CcdDataType
    limit: int
    exposure: int | None = None
    day_obs: int | None = None


@dataclass
class VisitEntry:
    id: str
    day_obs: int
    physical_filter: str
    obs_id: str
    exposure_time: float
    science_program: str
    observation_type: str
    observation_reason: str
    target_name: str


class DataSourceBase(abc.ABC):
    @abc.abstractmethod
    def query_visits(self, q: Query) -> list[VisitEntry]:  # pragma: no cover
        ...

    @abc.abstractmethod
    def list_ccds(self, visit: Visit) -> list[str]:  # pragma: no cover
        ...

    @abc.abstractmethod
    def get_data(self, ccd_id: CcdId) -> bytes:  # pragma: no cover
        ...

    @abc.abstractmethod
    def get_metadata(self, ccd_id: CcdId) -> 'DataSourceCcdMetadata':  # pragma: no cover
        ...

    @abc.abstractmethod
    def get_exposure_data_types(self, exposure_id: int) -> list[CcdDataType]: ...


@dataclass
class DataSourceCcdMetadata:
    visit: Visit
    ccd_name: str

    detector: int
    exposure: int
    day_obs: int
    uuid: str
