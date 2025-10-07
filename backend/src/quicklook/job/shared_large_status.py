from dataclasses import dataclass, field

from quicklook.comm.types import GeneratorId
from quicklook.generator.generate_single_fits_tiles import CcdMetadata
from quicklook.job.job import Job
from quicklook.types import CcdName


@dataclass
class JobSharedLargeStatus:
    job: Job

    ccd_generator_map: dict[CcdName, GeneratorId] = field(default_factory=dict)
    ccd_metadata_list: list[CcdMetadata] = field(default_factory=list)

    @classmethod
    def from_job(cls, job: Job) -> 'JobSharedLargeStatus':
        return cls(job)
