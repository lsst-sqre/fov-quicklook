import time
from dataclasses import dataclass
from enum import Enum

from pydantic import BaseModel, Field

from quicklook.types import GenerateProgress, GeneratorPod, MergeProgress, TransferProgress, Visit


class QuicklookJobPhase(int, Enum):
    QUEUED = 0
    GENERATE_RUNNING = 1
    GENERATE_DONE = 2
    MERGE_RUNNING = 3
    MERGE_DONE = 4
    TRANSFER_RUNNING = 5
    TRANSFER_DONE = 6
    READY = 7
    FAILED = -1


class QuicklookJob(BaseModel):
    visit: Visit
    phase: QuicklookJobPhase
    no_transfer: bool
    created_at: float = Field(default_factory=time.time)

    generate_progress: dict[str, GenerateProgress] | None = None
    merge_progress: dict[str, MergeProgress] | None = None
    transfer_progress: dict[str, TransferProgress] | None = None

    ccd_generator_map: dict[str, GeneratorPod] | None = None
    # ccd_name -> GeneratorPod
    # どのGeneratorがどのCCDを処理するかを示す
    # transferreing中にFrontendがどのどこからデータを取得するかを知るために必要


@dataclass
class QuicklookJobReport:
    # このデータクラスはFrontendに共有するためのもの
    # このデータクラスはQuicklookJobの一部を持つ
    visit: Visit
    phase: QuicklookJobPhase
    created_at: float
    generate_progress: dict[str, GenerateProgress] | None
    merge_progress: dict[str, MergeProgress] | None
    transfer_progress: dict[str, TransferProgress] | None

    @classmethod
    def from_job(cls, job: QuicklookJob) -> 'QuicklookJobReport':
        return cls(
            visit=job.visit,
            phase=job.phase,
            created_at=job.created_at,
            generate_progress=job.generate_progress,
            transfer_progress=job.transfer_progress,
            merge_progress=job.merge_progress,
        )
    