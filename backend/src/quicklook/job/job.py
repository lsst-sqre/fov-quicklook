import uuid
from dataclasses import dataclass, field
from functools import cached_property

from quicklook.types import VisitName
from quicklook.utils.exclude_cached_properties_from_pickle import exclude_cached_properties_from_pickle


@exclude_cached_properties_from_pickle
@dataclass(frozen=True)
class Job:
    visit: VisitName
    id: str = field(default_factory=lambda: f'j-{uuid.uuid4().hex}')

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

        return VisitObjectStorage.from_visit(self.visit)

    @cached_property
    def status(self):
        from .status import JobStatus

        s = JobStatus.from_job(self)
        return s

    @cached_property
    def priority(self):
        from .priority import JobPriority

        return JobPriority.from_job(self)
