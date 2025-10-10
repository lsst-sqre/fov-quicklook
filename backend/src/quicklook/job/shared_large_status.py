from dataclasses import dataclass, field

from quicklook.generator.generate_single_fits_tiles import CcdMetadata
from quicklook.job.job import Job
from quicklook.job.local_storage import CcdDistributionConfig


@dataclass
class JobSharedLargeStatus:
    job: Job

    dist_config: CcdDistributionConfig = field(default_factory=lambda: CcdDistributionConfig({}, {}))
    ccd_metadata_list: list[CcdMetadata] = field(default_factory=list)

    @classmethod
    def from_job(cls, job: Job) -> 'JobSharedLargeStatus':
        return cls(job)
