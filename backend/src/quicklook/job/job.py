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
    def from_visit(cls, visit: VisitName):
        return cls(visit=visit)

    @classmethod
    def from_id(cls, id: str):
        from quicklook.job.job_local_storage import JobLocalStorage

        return JobLocalStorage.from_id(id).job

    @cached_property
    def local_storage(self):
        from .job_local_storage import JobLocalStorage

        return JobLocalStorage.from_job(self)

    @cached_property
    def object_storage(self):
        from quicklook.object_storage import VisitObjectStorage

        return VisitObjectStorage.from_visit(self.visit)

    @cached_property
    def status(self):
        from quicklook.job.job_status import JobStatus

        return JobStatus.from_job(self)
