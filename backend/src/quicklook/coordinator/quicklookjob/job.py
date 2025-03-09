import time
from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel, Field

from quicklook.types import GenerateProgress, GeneratorPod, TransferProgress, Visit

QuicklookJobPhase = Literal['generate:queued', 'generate:running', 'transfer:queued', 'transfer:running', 'ready', 'failed']


class QuicklookJob(BaseModel):
    visit: Visit
    phase: QuicklookJobPhase
    created_at: float = Field(default_factory=time.time)

    generate_progress: dict[str, GenerateProgress] | None = None
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
    transfer_progress: dict[str, TransferProgress] | None

    @classmethod
    def from_job(cls, job: QuicklookJob) -> 'QuicklookJobReport':
        return cls(
            visit=job.visit,
            phase=job.phase,
            created_at=job.created_at,
            generate_progress=job.generate_progress,
            transfer_progress=job.transfer_progress,
        )
