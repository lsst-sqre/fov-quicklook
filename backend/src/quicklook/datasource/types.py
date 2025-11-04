import abc
import asyncio
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
    def query_visits_sync(self, q: Query) -> list[VisitEntry]:  # pragma: no cover
        ...

    async def query_visits(self, q: Query) -> list[VisitEntry]:  # pragma: no cover
        return await asyncio.to_thread(self.query_visits_sync, q)

    @abc.abstractmethod
    def list_ccds_sync(self, visit: VisitName) -> list[CcdName]:  # pragma: no cover
        ...

    async def list_ccds(self, visit: VisitName) -> list[CcdName]:  # pragma: no cover
        return await asyncio.to_thread(self.list_ccds_sync, visit)

    @abc.abstractmethod
    def get_data_sync(self, ref: CcdDataRef) -> bytes:  # pragma: no cover
        ...

    async def get_data(self, ref: CcdDataRef) -> bytes:  # pragma: no cover
        return await asyncio.to_thread(self.get_data_sync, ref)

    @abc.abstractmethod
    def get_metadata_sync(self, ref: CcdDataRef) -> 'DataSourceCcdMetadata':  # pragma: no cover
        ...

    async def get_metadata(self, ref: CcdDataRef) -> 'DataSourceCcdMetadata':  # pragma: no cover
        return await asyncio.to_thread(self.get_metadata_sync, ref)

    @abc.abstractmethod
    def get_exposure_data_types_sync(self, exposure_id: int) -> list[CcdDataType]:  # pragma: no cover
        ...

    async def get_exposure_data_types(self, exposure_id: int) -> list[CcdDataType]:  # pragma: no cover
        return await asyncio.to_thread(self.get_exposure_data_types_sync, exposure_id)


@dataclass
class DataSourceCcdMetadata:
    visit_name: VisitName
    ccd_name: CcdName

    detector: int
    exposure: int
    day_obs: int
    uuid: str
