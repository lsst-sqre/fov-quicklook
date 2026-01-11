"""
CCD処理用WebSocketプロトコル定義

Coordinator ↔ Generator 間のメッセージ形式を定義する。
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

from quicklook.generator.preprocess_ccd import AmpMetadata, ImageStat
from quicklook.types import CcdDataRef, CcdName, Progress
from quicklook.utils.geom import BBox

if TYPE_CHECKING:
    from quicklook.job.job import Job


# ============================================================
# Coordinator → Generator メッセージ
# ============================================================


@dataclass
class InitJobMessage:
    """Jobオブジェクトを送信してセッションを初期化"""
    type: Literal["init"] = "init"
    job: "Job | None" = None


@dataclass
class AssignCcdMessage:
    """CCDの処理を割り当てる"""
    type: Literal["assign"] = "assign"
    ccd_ref: CcdDataRef | None = None


@dataclass
class CancelMessage:
    """処理をキャンセル（通常はWebSocket切断で代用）"""
    type: Literal["cancel"] = "cancel"


# ============================================================
# Generator → Coordinator メッセージ
# ============================================================


@dataclass
class ProgressMessage:
    """処理進捗を通知"""
    type: Literal["progress"] = "progress"
    ccd_name: CcdName = CcdName("")
    stage: Literal["downloading", "preprocessing", "generating", "done"] = "downloading"
    progress: Progress | None = None


@dataclass
class CompletedMessage:
    """CCD処理完了を通知"""
    type: Literal["completed"] = "completed"
    ccd_name: CcdName = CcdName("")
    image_stat: ImageStat | None = None
    amps: list[AmpMetadata] | None = None
    bbox: BBox | None = None


@dataclass
class ErrorMessage:
    """エラーを通知"""
    type: Literal["error"] = "error"
    ccd_name: CcdName | None = None
    error: str = ""


@dataclass
class ReadyMessage:
    """スロットが空いたことを通知（未使用、拡張用）"""
    type: Literal["ready"] = "ready"
    available_slots: int = 0


# メッセージ型の Union
CoordinatorMessage = InitJobMessage | AssignCcdMessage | CancelMessage
GeneratorMessage = ProgressMessage | CompletedMessage | ErrorMessage | ReadyMessage
