"""
CCD処理用WebSocketプロトコル定義

Coordinator ↔ Generator 間のメッセージ形式を定義する。
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Literal

from quicklook.generator.preprocess_ccd import AmpMetadata, ImageStat
from quicklook.types import CcdDataRef, CcdName, Progress
from quicklook.utils.geom import BBox

if TYPE_CHECKING:
    from quicklook.job.job import Job


# ============================================================
# タイムプロファイル用データ構造
# ============================================================


@dataclass
class CcdTiming:
    """CCD処理の各ステップのタイミング情報（秒単位）"""
    ccd_name: CcdName
    generator_id: str = ""
    # Generator側の処理時間（秒）
    download_s: float | None = None
    preprocess_s: float | None = None
    generate_tiles_s: float | None = None
    save_header_s: float | None = None
    # Coordinator側の受信タイムスタンプ（ISO形式）
    assigned_at: str | None = None
    download_received_at: str | None = None
    preprocess_received_at: str | None = None
    generate_tiles_received_at: str | None = None
    completed_received_at: str | None = None


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
    # 処理時間（秒）- そのステージの処理時間を含む（完了時のみ）
    elapsed_s: float | None = None


@dataclass
class CompletedMessage:
    """CCD処理完了を通知"""
    type: Literal["completed"] = "completed"
    ccd_name: CcdName = CcdName("")
    image_stat: ImageStat | None = None
    amps: list[AmpMetadata] | None = None
    bbox: BBox | None = None
    # 各ステップの処理時間（秒）
    download_s: float | None = None
    preprocess_s: float | None = None
    generate_tiles_s: float | None = None
    save_header_s: float | None = None


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
