from pydantic import BaseModel

from quicklook.job.shared_large_status import JobSharedLargeStatus
from quicklook.job.status import JobStatus
from quicklook.types import VisitName


type JobStatusList = dict[VisitName, JobStatus]


class CreateQuicklookRequest(BaseModel):
    visit: str


class SharedStatusMessageJobStatusList(BaseModel):
    data: JobStatusList


class SharedStatusMessageJobSharedLargeStatus(BaseModel):
    visit: VisitName
    data: JobSharedLargeStatus


type SharedStatusMessage = SharedStatusMessageJobStatusList | SharedStatusMessageJobSharedLargeStatus