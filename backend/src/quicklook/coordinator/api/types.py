from pydantic import BaseModel
from quicklook.job.status import JobStatus
from quicklook.types import VisitName


type JobStatusList = dict[VisitName, JobStatus]


class CreateQuicklookRequest(BaseModel):
    visit: str