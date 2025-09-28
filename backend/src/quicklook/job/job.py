import uuid
from dataclasses import dataclass, field

from quicklook.types import VisitName


@dataclass(frozen=True)
class Job:
    visit: VisitName
    id: str = field(default_factory=lambda: f'j-{uuid.uuid4().hex}')

    @classmethod
    def from_id(cls, id: str):
        from quicklook.job.job_local_storage import JobLocalStorage

        return JobLocalStorage.from_id(id).job

    @property
    def local_storage(self):
        # この辺りをcached_propertyにしないのは
        # Jobは頻繁にpickleされてプロセスやノード間を転送されるから。
        from .job_local_storage import JobLocalStorage

        return JobLocalStorage.from_job(self)

    @property
    def object_storage(self):
        from quicklook.object_storage import VisitObjectStorage

        return VisitObjectStorage.from_visit(self.visit)

    @property
    def status(self):
        from quicklook.job.job_status import JobStatus

        return JobStatus.from_job(self)
