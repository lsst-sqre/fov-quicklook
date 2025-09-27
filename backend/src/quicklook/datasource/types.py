import abc
from dataclasses import dataclass

from quicklook.types import CcdDataRef, CcdDataType, CcdName, VisitName


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
    def list_ccds(self, visit: VisitName) -> list[CcdName]:  # pragma: no cover
        ...

    @abc.abstractmethod
    def get_data(self, ref: CcdDataRef) -> bytes:  # pragma: no cover
        ...

    @abc.abstractmethod
    def get_metadata(self, ref: CcdDataRef) -> 'DataSourceCcdMetadata':  # pragma: no cover
        ...

    @abc.abstractmethod
    def get_exposure_data_types(self, exposure_id: int) -> list[CcdDataType]: ...


@dataclass
class DataSourceCcdMetadata:
    visit_name: VisitName
    ccd_name: CcdName

    detector: int
    exposure: int
    day_obs: int
    uuid: str
