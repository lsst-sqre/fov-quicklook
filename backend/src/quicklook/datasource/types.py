import abc
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from quicklook.datasets import get_dataset
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
    repository_name: str
    collection: str
    dataset_type: str
    limit: int
    offset: int = 0
    where: str | None = None
    order_by: str | None = None
    reverse: bool | None = None


@dataclass
class VisitDayCountQuery:
    repository_name: str
    collection: str
    dataset_type: str
    calendar_month: str


@dataclass
class VisitEntry:
    id: str
    display_id: str
    scope_id: str
    day_obs: int
    physical_filter: str
    obs_id: str
    exposure_time: float
    science_program: str
    observation_type: str
    observation_reason: str
    target_name: str
    uuid: str | None = None
    utc_start: datetime | None = None


def sort_visit_entries(
    entries: list['VisitEntry'],
    *,
    dataset_type: str,
    order_by: str | None,
    reverse: bool | None,
) -> list['VisitEntry']:
    default = get_dataset(dataset_type).default_order_by[0]
    selected_field = order_by or default.removeprefix('-')
    selected_reverse = default.startswith('-') if selected_field == default.removeprefix('-') else False
    if reverse:
        selected_reverse = not selected_reverse
    return sorted(
        entries,
        key=lambda entry: (_visit_entry_sort_value(entry, selected_field), entry.display_id),
        reverse=selected_reverse,
    )


def _visit_entry_sort_value(entry: 'VisitEntry', field: str) -> Any:
    match field:
        case 'exposure' | 'visit':
            visit = VisitName(entry.id)
            value = visit.dimensions.get(field)
            return -1 if value is None else int(value)
        case _:
            return getattr(entry, field)


@dataclass
class VisitDayCount:
    day_obs: int
    count: int


@dataclass
class VisitRepresentativeUuid:
    uuid: str


@dataclass
class QueryWhereExample:
    label: str
    where: str


@dataclass
class QueryBuilderOptions:
    repositories: list[str]
    collections: list[str]
    dataset_types: list[str]
    where_examples: list[QueryWhereExample]
    collections_truncated: bool = False
    dataset_types_truncated: bool = False


class DataSourceBase(abc.ABC):
    @abc.abstractmethod
    def query_visits_sync(self, q: Query) -> list[VisitEntry]:  # pragma: no cover
        ...

    query_visits = async_wrap(query_visits_sync)

    @abc.abstractmethod
    def query_visit_day_counts_sync(self, q: VisitDayCountQuery) -> list[VisitDayCount]:  # pragma: no cover
        ...

    query_visit_day_counts = async_wrap(query_visit_day_counts_sync)

    @abc.abstractmethod
    def get_query_builder_options_sync(
        self,
        *,
        repository_name: str | None = None,
        collection: str | None = None,
        dataset_type: str | None = None,
    ) -> QueryBuilderOptions:  # pragma: no cover
        ...

    get_query_builder_options = async_wrap(get_query_builder_options_sync)

    def warm_query_builder_options_metadata_sync(self) -> None:
        return None

    warm_query_builder_options_metadata = async_wrap(warm_query_builder_options_metadata_sync)

    @abc.abstractmethod
    def resolve_visit_sync(self, visit: VisitName) -> VisitName:  # pragma: no cover
        ...

    resolve_visit = async_wrap(resolve_visit_sync)

    def resolve_visit_info_sync(self, visit: VisitName) -> ResolvedVisitInfo:
        return ResolvedVisitInfo(visit_name=self.resolve_visit_sync(visit))

    resolve_visit_info = async_wrap(resolve_visit_info_sync)

    @abc.abstractmethod
    def get_visit_representative_uuid_sync(self, visit: VisitName) -> str:  # pragma: no cover
        ...

    get_visit_representative_uuid = async_wrap(get_visit_representative_uuid_sync)

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


@dataclass
class DataSourceCcdMetadata:
    visit_name: VisitName
    ccd_name: CcdName

    detector: int
    exposure: int
    day_obs: int
    uuid: str
