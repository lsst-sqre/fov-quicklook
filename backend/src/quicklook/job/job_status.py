from dataclasses import dataclass, field
from functools import lru_cache
from typing import Literal

from quicklook.config import config
from quicklook.job.job import Job
from quicklook.types import CcdName, Progress

JobPhase = Literal['generate_single_fits_tiles', 'merge_tiles', 'transfer_tiles']

GeneratorId = str


@dataclass
class JobStatus:
    job: Job

    generate_single_fits_tiles: dict[CcdName, Progress] = field(default_factory=dict)
    merge_tiles: dict[GeneratorId, Progress] = field(default_factory=dict)
    transfer_tiles: dict[GeneratorId, Progress] = field(default_factory=dict)

    @classmethod
    @lru_cache(config.max_job)
    def from_job(cls, job: Job) -> 'JobStatus':
        return cls(job)

    def notify(self):
        from .job_status_printer import display_status

        display_status(self)
