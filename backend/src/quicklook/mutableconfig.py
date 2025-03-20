from typing import Literal
from pydantic import BaseModel
from quicklook.coordinator.quicklookjob.job import QuicklookJobPhase


class MutableConfig(BaseModel):
    job_stop_at: Literal['READY', 'GENERATE_DONE', 'MERGE_DONE'] = 'READY'


mutable_config = MutableConfig()


def update_mutable_config(new: dict):
    new_config = MutableConfig.model_validate({**mutable_config.model_dump(), **new})
    for k in new.keys():
        setattr(mutable_config, k, getattr(new_config, k))
