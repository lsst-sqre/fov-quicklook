import abc
from dataclasses import dataclass

from quicklook.types import CcdDataRef, CcdDataType, CcdName, VisitName
from quicklook.utils.async_wrap import async_wrap


class VisitResolutionError(ValueError):
    pass


@dataclass
class ResolvedVisitInfo:
    visit_name: VisitName
    detector: int | None = None


@dataclass
class Query:
    data_type: CcdDataType
    repository_name: str
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


@dataclass
class MonthlyEntryCountQuery:
    data_type: CcdDataType
    repository_name: str
    year: int
    month: int


@dataclass
class VisitDayCount:
    day_obs: int
    count: int


class DataSourceBase(abc.ABC):
    @abc.abstractmethod
    def query_visits_sync(self, q: Query) -> list[VisitEntry]:  # pragma: no cover
        ...

    query_visits = async_wrap(query_visits_sync)

    @abc.abstractmethod
    def resolve_visit_sync(self, visit: VisitName) -> VisitName:  # pragma: no cover
        ...

    resolve_visit = async_wrap(resolve_visit_sync)

    def resolve_visit_info_sync(self, visit: VisitName) -> ResolvedVisitInfo:
        return ResolvedVisitInfo(visit_name=self.resolve_visit_sync(visit))

    resolve_visit_info = async_wrap(resolve_visit_info_sync)

    @abc.abstractmethod
    def list_ccds_sync(self, visit: VisitName) -> list[CcdName]:  # pragma: no cover
        ...

    list_ccds = async_wrap(list_ccds_sync)

    @abc.abstractmethod
    def get_data_sync(self, ref: CcdDataRef) -> bytes:  # pragma: no cover
        ...

    get_data = async_wrap(get_data_sync)

    @abc.abstractmethod
    def get_metadata_sync(self, ref: CcdDataRef) -> 'DataSourceCcdMetadata':  # pragma: no cover
        ...

    get_metadata = async_wrap(get_metadata_sync)

    @abc.abstractmethod
    def get_exposure_data_types_sync(self, exposure_id: int) -> list[CcdDataType]:  # pragma: no cover
        ...

    get_exposure_data_types = async_wrap(get_exposure_data_types_sync)

    @abc.abstractmethod
    def query_monthly_entry_counts_sync(self, q: MonthlyEntryCountQuery) -> list[VisitDayCount]:  # pragma: no cover
        ...

    query_monthly_entry_counts = async_wrap(query_monthly_entry_counts_sync)


@dataclass
class DataSourceCcdMetadata:
    visit_name: VisitName
    ccd_name: CcdName

    detector: int
    exposure: int
    day_obs: int
    uuid: str
