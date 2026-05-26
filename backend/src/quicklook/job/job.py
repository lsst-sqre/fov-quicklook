import uuid
from dataclasses import dataclass, field
from functools import cached_property

from quicklook.config import config
from quicklook.types import VisitName
from quicklook.utils.exclude_cached_properties_from_pickle import exclude_cached_properties_from_pickle


@exclude_cached_properties_from_pickle
@dataclass(frozen=True)
class Job:
    visit: VisitName
    id: str = field(default_factory=lambda: f'j-{uuid.uuid4().hex}')
    cache_version: int = field(default_factory=lambda: config.tile_cache_schema_version)

    @classmethod
    def from_id(cls, id: str):
        from quicklook.job.local_storage import JobLocalStorage

        return JobLocalStorage.from_id(id).job

    @cached_property
    def local_storage(self):
        from .local_storage import JobLocalStorage

        return JobLocalStorage.from_job(self)

    @cached_property
    def object_storage(self):
        from quicklook.object_storage import VisitObjectStorage

        return VisitObjectStorage.from_visit(self.visit, cache_version=self.cache_version)

    @cached_property
    def status(self):
        from .status import JobStatus

        return JobStatus.from_job(self)

    @cached_property
    def watcher(self):
        from .watcher import JobWatcher

        return JobWatcher.from_job(self)

    @cached_property
    def priority(self):
        from .priority import JobPriority

        return JobPriority.from_job(self)

    @cached_property
    def shared_large_status(self):
        from .shared_large_status import JobSharedLargeStatus

        return JobSharedLargeStatus.from_job(self)
