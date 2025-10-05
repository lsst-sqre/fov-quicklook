import itertools
from dataclasses import dataclass, field
from typing import ClassVar

from quicklook.job.job import Job


@dataclass
class JobPriority:
    __seq: ClassVar = itertools.count()

    job: Job
    user_count: int = 1
    seq: int = field(default_factory=lambda: next(JobPriority.__seq))

    @classmethod
    def from_job(cls, job: Job):
        return cls(job)

    def sort_key(self: "JobPriority"):
        return -self.user_count, self.seq

    def __hash__(self) -> int:
        return hash(self.job)
