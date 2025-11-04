from dataclasses import dataclass, field
from typing import Literal

from quicklook.comm.types import GeneratorId
from quicklook.job.job import Job
from quicklook.types import CcdName, Progress

JobStage = Literal['queued', 'generate_single_fits_tiles', 'merge_tiles', 'upload_to_object_storage', 'ready', 'error']


@dataclass
class JobStatus:
    job: Job

    stage: JobStage = 'queued'
    generate_single_fits_tiles: dict[CcdName, Progress] = field(default_factory=dict)
    merge_tiles: dict[GeneratorId, Progress] = field(default_factory=dict)
    transfer_tiles: dict[GeneratorId, Progress] = field(default_factory=dict)
    error_message: str | None = None

    @classmethod
    def from_job(cls, job: Job) -> 'JobStatus':
        return cls(job)
