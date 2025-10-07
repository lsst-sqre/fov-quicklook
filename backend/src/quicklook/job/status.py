from dataclasses import dataclass, field
from typing import Literal

from quicklook.comm.types import GeneratorId
from quicklook.job.job import Job
from quicklook.types import CcdName, Progress

JobStage = Literal['queued', 'generate_single_fits_tiles', 'merge_tiles', 'transfer_tiles', 'done']


@dataclass
class JobStatus:
    job: Job

    stage: JobStage = 'queued'
    generate_single_fits_tiles: dict[CcdName, Progress] = field(default_factory=dict)
    merge_tiles: dict[GeneratorId, Progress] = field(default_factory=dict)
    transfer_tiles: dict[GeneratorId, Progress] = field(default_factory=dict)
    ccd_generator_map: dict[CcdName, GeneratorId] = field(default_factory=dict)

    @classmethod
    def from_job(cls, job: Job) -> 'JobStatus':
        return cls(job)
