"""
CcdDispatcher: CCD動的割り当て管理

Phase 1: 初期ディスパッチ - 全CCDを順次Generatorに割り当て
Phase 2: 再ディスパッチ - 未完了CCDを古い順にラウンドロビンで再submit
"""

import asyncio
import time
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime

import quicklook.mylogging
from quicklook.comm.types import GeneratorId
from quicklook.config import config
from quicklook.generator.generate_single_fits_tiles import CcdMetadata
from quicklook.job.time_profile import CcdProfile, GeneratorProfile
from quicklook.types import CcdDataRef, CcdName

logger = quicklook.mylogging.getLogger(__name__)


@dataclass
class CcdSubmission:
    """CCD submit履歴を追跡するためのデータ構造"""
    ccd_ref: CcdDataRef
    submitted_at: datetime
    generator_id: GeneratorId


class CcdDispatcher:
    """
    CCD割り当てを管理するクラス。

    Phase 1: 初期ディスパッチ - 全CCDを順次Generatorに割り当て
    Phase 2: 再ディスパッチ - 未完了CCDを古い順にラウンドロビンで再submit

    これにより、遅いGeneratorに割り当てられたCCDを
    空きスロットのある他のGeneratorに再割り当てできる。
    """

    def __init__(
        self,
        ccd_refs: Sequence[CcdDataRef],
        resubmit_min_age_seconds: float = config.resubmit_min_age_seconds,
        resubmit_max_attempts_per_ccd: int = config.resubmit_max_attempts_per_ccd,
    ):
        self._ccd_refs = list(ccd_refs)
        self._remaining_index = 0  # Phase 1用: 次にsubmitするCCDのインデックス
        self._submitted_ccds: list[CcdSubmission] = []  # submit履歴（Phase 2用）
        self._ccd_metadata_dict: dict[CcdName, CcdMetadata] = {}  # 完了メタデータ
        self._ccd_generator_map: dict[CcdName, GeneratorId] = {}  # 最終的な担当Generator
        self._phase2_index = 0  # Phase 2用ラウンドロビンインデックス
        self._attempts: dict[CcdName, int] = defaultdict(int)  # submit回数追跡
        self._all_completed = asyncio.Event()  # 全完了通知用
        self._ccd_available_condition = asyncio.Condition()  # CCD再割り当て可能通知
        self._lock = asyncio.Lock()

        # 再submit暴走防止パラメータ
        self._resubmit_min_age_seconds = resubmit_min_age_seconds
        self._resubmit_max_attempts_per_ccd = resubmit_max_attempts_per_ccd

        # アクティブなGenerator追跡
        self._active_generators: set[GeneratorId] = set()

        # CCD処理タイミング: 最初にassignした時刻を記録
        self._ccd_assign_time: dict[CcdName, float] = {}
        self._ccd_complete_time: dict[CcdName, float] = {}

        # Generator稼働タイミング
        self._generator_start_time: dict[GeneratorId, float] = {}
        self._generator_end_time: dict[GeneratorId, float] = {}
        self._generator_ccd_count: dict[GeneratorId, int] = defaultdict(int)

    @property
    def ccd_metadata_dict(self) -> dict[CcdName, CcdMetadata]:
        return self._ccd_metadata_dict

    @property
    def ccd_generator_map(self) -> dict[CcdName, GeneratorId]:
        return self._ccd_generator_map

    @property
    def all_completed(self) -> asyncio.Event:
        return self._all_completed

    @property
    def ccd_available_condition(self) -> asyncio.Condition:
        return self._ccd_available_condition

    def register_generator(self, generator_id: GeneratorId) -> None:
        """Generatorをアクティブとして登録する"""
        self._active_generators.add(generator_id)

    async def on_generator_lost(self, generator_id: GeneratorId) -> None:
        """
        Generator消失時の処理。

        消失したGeneratorが処理中だったCCDのsubmit時刻を古い値に書き換え、
        即座にPhase 2の再submit対象にする。
        また、ccd_availableイベントを発火して他のworkerに通知する。
        """
        async with self._lock:
            self._active_generators.discard(generator_id)
            reassigned_count = 0
            epoch = datetime(2000, 1, 1)  # 十分古い時刻
            for submission in self._submitted_ccds:
                if submission.generator_id == generator_id:
                    ccd_name = submission.ccd_ref.ccd
                    if ccd_name not in self._ccd_metadata_dict:
                        submission.submitted_at = epoch
                        reassigned_count += 1
            if reassigned_count > 0:
                logger.warning(
                    f"Generator {generator_id} lost: {reassigned_count} CCDs now eligible for resubmit"
                )

            if not self._active_generators and len(self._ccd_metadata_dict) < len(self._ccd_refs):
                logger.error("All generators lost before processing completed")

        if reassigned_count > 0:
            async with self._ccd_available_condition:
                self._ccd_available_condition.notify_all()

    async def get_next_ccd(self, generator_id: GeneratorId) -> CcdDataRef | None:
        """
        次に処理すべきCCDを取得する。

        Phase 1: 未submitのCCDがあれば優先的に割り当て
        Phase 2: 全CCDがsubmit済みなら、未完了CCDを再submit

        Returns:
            次に処理すべきCCD、または全て完了していればNone
        """
        async with self._lock:
            # 全完了チェック
            if len(self._ccd_metadata_dict) == len(self._ccd_refs):
                return None

            # Phase 1: 未submitのCCDがあれば優先
            if self._remaining_index < len(self._ccd_refs):
                ccd_ref = self._ccd_refs[self._remaining_index]
                self._remaining_index += 1
                self._submitted_ccds.append(
                    CcdSubmission(ccd_ref, datetime.now(), generator_id)
                )
                self._attempts[ccd_ref.ccd] += 1
                # 初回assignの時刻を記録
                if ccd_ref.ccd not in self._ccd_assign_time:
                    self._ccd_assign_time[ccd_ref.ccd] = time.time()
                logger.info(f"Phase1 assign: CCD {ccd_ref.ccd} → {generator_id} (index={self._remaining_index-1}, total_submitted={self._remaining_index})")
                return ccd_ref

            # Phase 2: 未完了CCDを（提出順の）ラウンドロビンで再submit
            if self._resubmit_max_attempts_per_ccd <= 0:
                # 再submit無効化
                return None

            now = datetime.now()
            skipped_young = 0
            skipped_maxattempts = 0
            for offset in range(len(self._submitted_ccds)):
                idx = (self._phase2_index + offset) % len(self._submitted_ccds)
                submission = self._submitted_ccds[idx]
                ccd_name = submission.ccd_ref.ccd

                # 既に完了したCCDは対象外
                if ccd_name in self._ccd_metadata_dict:
                    continue

                # 暴走防止: 一定時間以上"古い"in-flightのみ
                age_seconds = (now - submission.submitted_at).total_seconds()
                if age_seconds < self._resubmit_min_age_seconds:
                    skipped_young += 1
                    continue

                # 暴走防止: 再submit上限チェック
                if self._attempts[ccd_name] > self._resubmit_max_attempts_per_ccd:
                    skipped_maxattempts += 1
                    continue

                self._attempts[ccd_name] += 1
                self._phase2_index = (idx + 1) % len(self._submitted_ccds)
                remaining_incomplete = len(self._ccd_refs) - len(self._ccd_metadata_dict)
                logger.info(
                    f"Phase2 resubmit: CCD {ccd_name} → {generator_id} "
                    f"(age={age_seconds:.1f}s, attempt={self._attempts[ccd_name]}, "
                    f"remaining_incomplete={remaining_incomplete})"
                )
                return submission.ccd_ref

            if skipped_young > 0 or skipped_maxattempts > 0:
                remaining_incomplete = len(self._ccd_refs) - len(self._ccd_metadata_dict)
                logger.info(
                    f"Phase2 no resubmit candidate for {generator_id}: "
                    f"skipped_young={skipped_young}, skipped_maxattempts={skipped_maxattempts}, "
                    f"remaining_incomplete={remaining_incomplete}"
                )

            return None

    async def on_ccd_completed(
        self,
        ccd_name: CcdName,
        metadata: CcdMetadata,
        generator_id: GeneratorId,
    ) -> None:
        """
        CCD処理完了を記録する。

        最初の完了のみ採用（重複処理の結果は破棄）。
        """
        async with self._lock:
            # 最初の完了のみ採用
            if ccd_name not in self._ccd_metadata_dict:
                self._ccd_metadata_dict[ccd_name] = metadata
                self._ccd_generator_map[ccd_name] = generator_id
                self._ccd_complete_time[ccd_name] = time.time()
                self._generator_ccd_count[generator_id] += 1

                completed = len(self._ccd_metadata_dict)
                total = len(self._ccd_refs)
                remaining = total - completed
                assign_time = self._ccd_assign_time.get(ccd_name, 0.0)
                elapsed = self._ccd_complete_time[ccd_name] - assign_time if assign_time > 0 else 0.0
                logger.info(
                    f"CCD {ccd_name} completed: {completed}/{total} (remaining={remaining}) "
                    f"elapsed={elapsed:.1f}s generator={generator_id}"
                )

                if completed == total:
                    self._all_completed.set()

    async def return_unassigned_ccd(self, ccd_ref: CcdDataRef) -> None:
        """
        割り当てに失敗したCCDを返却する。

        WebSocket送信失敗時に呼ばれ、attemptカウンタを1つ戻して
        再度resubmit対象にする。ccd_available通知も送る。
        """
        async with self._lock:
            ccd_name = ccd_ref.ccd
            if ccd_name not in self._ccd_metadata_dict:
                if self._attempts[ccd_name] > 0:
                    self._attempts[ccd_name] -= 1
                logger.info(f"Returned unassigned CCD {ccd_name}, attempts now {self._attempts[ccd_name]}")
        async with self._ccd_available_condition:
            self._ccd_available_condition.notify_all()

    def record_generator_start(self, generator_id: GeneratorId) -> None:
        self._generator_start_time[generator_id] = time.time()
        self.register_generator(generator_id)

    def record_generator_end(self, generator_id: GeneratorId) -> None:
        self._generator_end_time[generator_id] = time.time()

    def build_ccd_profiles(self) -> list[CcdProfile]:
        profiles: list[CcdProfile] = []
        for ccd_name, complete_time in self._ccd_complete_time.items():
            assign_time = self._ccd_assign_time.get(ccd_name, 0.0)
            generator_id = self._ccd_generator_map.get(ccd_name, GeneratorId("unknown"))
            elapsed = complete_time - assign_time if assign_time > 0 else 0.0
            profiles.append(CcdProfile(ccd_name=ccd_name, generator_id=generator_id, elapsed=elapsed))
        return profiles

    def build_generator_profiles(self) -> list[GeneratorProfile]:
        profiles: list[GeneratorProfile] = []
        for generator_id, start_time in self._generator_start_time.items():
            end_time = self._generator_end_time.get(generator_id, start_time)
            elapsed = end_time - start_time
            ccd_count = self._generator_ccd_count.get(generator_id, 0)
            profiles.append(GeneratorProfile(generator_id=generator_id, elapsed=elapsed, ccd_count=ccd_count))
        return profiles
