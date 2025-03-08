import time
from dataclasses import dataclass, field
from typing import Literal

from quicklook.types import GeneratorPod, GeneratorProgress, Visit


@dataclass
class QuicklookJob:
    # このインスタンスがjob_managerを通してCoordinatorとFrontendで同期される
    
    Phase = Literal['generate:queued', 'generate:running', 'transfer:queued', 'transfer:running', 'ready', 'failed']

    visit: Visit
    phase: Phase
    created_at: float = field(default_factory=lambda: time.time())

    generate_progress: dict[str, GeneratorProgress] | None = None
    transfer_progress: float | None = None

    ccd_generator_map: dict[str, GeneratorPod] | None = None
    # ccd_name -> GeneratorPod
    # どのGeneratorがどのCCDを処理するかを示す
    # transferreing中にFrontendがどのどこからデータを取得するかを知るために必要
    # これはstorage経由の方が良いだろう
