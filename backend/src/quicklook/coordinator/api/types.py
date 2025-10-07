from typing import Literal

from pydantic import BaseModel

from quicklook.job.shared_large_status import JobSharedLargeStatus
from quicklook.job.status import JobStatus
from quicklook.types import VisitName


type JobStatusList = dict[VisitName, JobStatus]


class CreateQuicklookRequest(BaseModel):
    visit: str


class SharedStatusMessageJobStatusList(BaseModel):
    type: Literal['job_status_list'] = 'job_status_list'
    data: JobStatusList


class SharedStatusMessageJobSharedLargeStatus(BaseModel):
    type: Literal['job_shared_large_status'] = 'job_shared_large_status'
    visit: VisitName
    data: JobSharedLargeStatus


type SharedStatusMessage = SharedStatusMessageJobStatusList | SharedStatusMessageJobSharedLargeStatus