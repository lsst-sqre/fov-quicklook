"""
Generate Single FITS Tiles: Coordinator側実装

WebSocket API方式によるFITSタイル生成。
各Generatorに対してWebSocket接続を確立し、動的にCCDを割り当てながら処理を行う。
"""

import asyncio
import pickle
import time
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime

import aiohttp

import quicklook.mylogging
from quicklook.comm.coordinator import (
    get_available_generators,
    add_on_generator_registered_callback,
    remove_on_generator_registered_callback,
)
from quicklook.comm.rpc_worker import rpc_scatter
from quicklook.comm.types import GeneratorId, GeneratorInfo
from quicklook.config import config
from quicklook.generator.api.ccd_processing_protocol import (
    AssignCcdMessage,
    CompletedMessage,
    ErrorMessage,
    InitJobMessage,
    ProgressMessage,
)
from quicklook.generator.generate_single_fits_tiles import CcdMetadata
from quicklook.job.job import Job
from quicklook.job.local_storage import CcdDistributionConfig
from quicklook.job.time_profile import CcdProfile, GeneratorProfile
from quicklook.types import CcdDataRef, CcdName, Progress

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
                    ccd_name = submission.ccd_ref.ccd_name
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
                self._attempts[ccd_ref.ccd_name] += 1
                # 初回assignの時刻を記録
                if ccd_ref.ccd_name not in self._ccd_assign_time:
                    self._ccd_assign_time[ccd_ref.ccd_name] = time.time()
                return ccd_ref

            # Phase 2: 未完了CCDを（提出順の）ラウンドロビンで再submit
            if self._resubmit_max_attempts_per_ccd <= 0:
                # 再submit無効化
                return None

            for offset in range(len(self._submitted_ccds)):
                idx = (self._phase2_index + offset) % len(self._submitted_ccds)
                submission = self._submitted_ccds[idx]
                ccd_name = submission.ccd_ref.ccd_name

                # 既に完了したCCDは対象外
                if ccd_name in self._ccd_metadata_dict:
                    continue

                # 暴走防止: 一定時間以上"古い"in-flightのみ
                age_seconds = (datetime.now() - submission.submitted_at).total_seconds()
                if age_seconds < self._resubmit_min_age_seconds:
                    continue

                # 暴走防止: 再submit上限チェック
                if self._attempts[ccd_name] > self._resubmit_max_attempts_per_ccd:
                    continue

                self._attempts[ccd_name] += 1
                self._phase2_index = (idx + 1) % len(self._submitted_ccds)
                return submission.ccd_ref

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

                if len(self._ccd_metadata_dict) == len(self._ccd_refs):
                    self._all_completed.set()

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


@dataclass
class GenerateSingleFitsTilesResult:
    ccd_metadata_list: list[CcdMetadata]
    ccd_profiles: list[CcdProfile]
    generator_profiles: list[GeneratorProfile]


async def generate_single_fits_tiles_coordinator(job: Job, ccd_refs: list[CcdDataRef]) -> GenerateSingleFitsTilesResult:
    """
    WebSocket API方式によるFITSタイル生成

    各Generatorに対してWebSocket接続を確立し、
    動的にCCDを割り当てながら処理を行う。

    動的割り当ての利点:
      - 高速なジェネレータがより多くのCCDを処理
      - 低速なジェネレータがボトルネックにならない
      - 自動的に最適な負荷分散を実現

    遅延Generatorへの対策:
      - Phase 1: 全CCDを順次割り当て（従来の動的割り当て）
      - Phase 2: 未完了CCDを他のGeneratorに再割り当て
      - 最初に完了したGeneratorのみ採用、重複処理結果は破棄
    """
    ccd_refs = sorted(ccd_refs, key=lambda ref: ref.ccd_name)
    generators = get_available_generators()
    if not generators:
        raise RuntimeError("No generators available")

    generator_list = list(generators.values())
    dispatcher = CcdDispatcher(ccd_refs)
    max_concurrent_ccds = config.generator_max_concurrent_ccds_per_job
    max_worker_connect_retries = 3
    worker_connect_retry_interval = 2.0

    async def _run_worker_session(generator: GeneratorInfo) -> None:
        """
        GeneratorへのWebSocket接続を確立し、CCD処理ループを実行する。
        接続失敗時は呼び出し元でリトライする。
        """
        ws_url = f"{generator.ws_url}/jobs/{job.id}/generate-tiles"
        logger.info(f"Worker connecting to {ws_url}")

        timeout = aiohttp.ClientTimeout(total=None, connect=10, sock_connect=10, sock_read=None)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.ws_connect(ws_url) as ws:
                logger.info(f"Connected to generator {generator.id}")
                dispatcher.record_generator_start(generator.id)

                # 最初にJobオブジェクトを送信
                await ws.send_bytes(pickle.dumps(InitJobMessage(job=job)))
                logger.debug(f"Sent InitJobMessage to generator {generator.id}")

                # 初期バッチ割り当て
                has_initial_batch = False
                for _ in range(max_concurrent_ccds):
                    ccd_ref = await dispatcher.get_next_ccd(generator.id)
                    if ccd_ref is not None:
                        logger.debug(f"Assigning CCD {ccd_ref.ccd_name} to generator {generator.id}")
                        await ws.send_bytes(pickle.dumps(AssignCcdMessage(ccd_ref=ccd_ref)))
                        has_initial_batch = True

                if not has_initial_batch:
                    # 初期バッチがない場合、Phase 2での参加を待つ
                    ccd_ref = await _wait_for_next_ccd(dispatcher, generator.id)
                    if ccd_ref is None:
                        await ws.send_bytes(pickle.dumps(AssignCcdMessage(ccd_ref=None)))
                        return
                    await ws.send_bytes(pickle.dumps(AssignCcdMessage(ccd_ref=ccd_ref)))

                logger.info(f"Initial batch sent to generator {generator.id}, waiting for responses")
                end_signal_sent = False

                async def _send_end_signal_on_completion() -> None:
                    """all_completedを監視し、セットされたらend signalを送信する。
                    メインループがメッセージ待ちでブロックされている場合でも
                    end signalが確実に送信されるようにする。"""
                    nonlocal end_signal_sent
                    await dispatcher.all_completed.wait()
                    if not end_signal_sent:
                        end_signal_sent = True
                        logger.info(f"All CCDs completed, sending end signal to generator {generator.id}")
                        try:
                            await ws.send_bytes(pickle.dumps(AssignCcdMessage(ccd_ref=None)))
                        except Exception as e:
                            logger.debug(f"Failed to send end signal to {generator.id}: {e}")

                completion_task = asyncio.create_task(_send_end_signal_on_completion())
                try:
                    # メッセージ処理ループ
                    # end signal送信後、generatorは新規CCD受付を停止するが、
                    # 処理中CCDの結果は引き続き送信し、完了後にWebSocketを閉じる。
                    async for msg in ws:
                        if msg.type == aiohttp.WSMsgType.BINARY:
                            data = pickle.loads(msg.data)
                            logger.debug(f"Received message from generator {generator.id}: {type(data).__name__}")
                            await _handle_generator_message(
                                data, job, dispatcher, generator, ws
                            )

                        elif msg.type == aiohttp.WSMsgType.CLOSED:
                            logger.info(f"WebSocket closed by generator {generator.id}")
                            break
                        elif msg.type == aiohttp.WSMsgType.ERROR:
                            logger.error(f"WebSocket error from generator {generator.id}: {ws.exception()}")
                            break
                finally:
                    completion_task.cancel()
                    try:
                        await completion_task
                    except asyncio.CancelledError:
                        pass

    async def worker(generator: GeneratorInfo) -> None:
        """
        各Generatorのワーカー。
        WebSocket接続で動的にCCDを供給する。
        接続失敗時はgeneratorの最新情報を取得してリトライする。
        （rolling restart中はIPが変わるため）

        正常終了後も全CCD完了まで待機し、他のGenerator消失による
        resubmit CCDを拾うために新しいセッションを開始できる。
        """
        generator_id = generator.id
        current_generator = generator
        consecutive_failures = 0
        while not dispatcher.all_completed.is_set():
            try:
                await _run_worker_session(current_generator)
                consecutive_failures = 0

                if dispatcher.all_completed.is_set():
                    dispatcher.record_generator_end(generator_id)
                    return

                # 正常終了後、resubmit可能なCCDが出るまで待機
                ccd_ref = await _wait_for_next_ccd(dispatcher, generator_id)
                if ccd_ref is None:
                    dispatcher.record_generator_end(generator_id)
                    return  # 全完了

                # resubmit用の新しいセッションに入る前にgenerator情報を更新
                available = get_available_generators()
                if generator_id in available:
                    current_generator = available[generator_id]
                    logger.info(f"Worker {generator_id} starting new session for resubmit CCD {ccd_ref.ccd_name}")
                else:
                    logger.info(f"Generator {generator_id} no longer available after session, stopping worker")
                    dispatcher.record_generator_end(generator_id)
                    return

            except aiohttp.ClientError as e:
                consecutive_failures += 1
                if consecutive_failures >= max_worker_connect_retries:
                    logger.warning(
                        f"Generator {generator_id} connection failed {consecutive_failures} times, giving up"
                    )
                    break
                logger.warning(
                    f"Generator {generator_id} connection failed (attempt {consecutive_failures}/{max_worker_connect_retries}): {e}"
                )

                # リトライ前に待機し、最新のgenerator情報を取得
                await asyncio.sleep(worker_connect_retry_interval)
                available = get_available_generators()
                if generator_id in available:
                    current_generator = available[generator_id]
                    logger.info(f"Retrying with updated generator info: {current_generator.ws_url}")
                else:
                    logger.warning(f"Generator {generator_id} no longer available, stopping worker")
                    break

            except asyncio.CancelledError:
                raise
            except Exception as e:
                logger.error(f"Worker error for generator {generator_id}: {e}")
                break  # 予期しないエラーはリトライしない

        dispatcher.record_generator_end(generator_id)
        await dispatcher.on_generator_lost(generator_id)

    # 全workerを起動
    active_worker_generator_ids: set[GeneratorId] = {g.id for g in generator_list}
    worker_tasks = [asyncio.create_task(worker(g)) for g in generator_list]

    # 新しいgeneratorが登録されたときにworkerを動的に追加するコールバック
    def on_new_generator(generator_info: GeneratorInfo) -> None:
        if dispatcher.all_completed.is_set():
            return
        if generator_info.id in active_worker_generator_ids:
            # 既にこのgenerator_idのworkerがリトライ中の可能性がある。
            # workerのリトライ内で最新IPを取得するのでここでは起動しない。
            logger.debug(f"Worker already exists for generator {generator_info.id}, skipping")
            return
        logger.info(f"New generator registered during pipeline: {generator_info.id}, spawning worker")
        active_worker_generator_ids.add(generator_info.id)
        task = asyncio.create_task(worker(generator_info))
        worker_tasks.append(task)

    add_on_generator_registered_callback(on_new_generator)

    try:
        # 全CCD完了を待機（タイムアウト付き）
        timeout_seconds = config.generate_single_fits_tiles_timeout_seconds
        await asyncio.wait_for(dispatcher.all_completed.wait(), timeout=timeout_seconds)
    except asyncio.TimeoutError:
        completed_ccds = set(dispatcher.ccd_metadata_dict.keys())
        all_ccds = {ref.ccd_name for ref in ccd_refs}
        missing_ccds = all_ccds - completed_ccds
        logger.error(
            f"Timeout waiting for CCDs: {len(completed_ccds)}/{len(ccd_refs)} completed. "
            f"Missing CCDs: {sorted(missing_ccds)}"
        )
        raise RuntimeError(
            f"Timeout ({timeout_seconds}s) waiting for CCD processing: "
            f"got {len(dispatcher.ccd_metadata_dict)}/{len(ccd_refs)} metadata. "
            f"Missing: {sorted(missing_ccds)}"
        )
    finally:
        remove_on_generator_registered_callback(on_new_generator)
        # 残存workerをキャンセル
        for task in worker_tasks:
            if not task.done():
                task.cancel()
        await asyncio.gather(*worker_tasks, return_exceptions=True)

    if len(dispatcher.ccd_metadata_dict) != len(ccd_refs):
        raise RuntimeError(
            f"Not all CCDs processed: got {len(dispatcher.ccd_metadata_dict)}/{len(ccd_refs)} metadata"
        )

    dist_config = CcdDistributionConfig(dispatcher.ccd_generator_map, generators)
    async with job.watcher.notify_shared_large_status():
        job.shared_large_status.dist_config = dist_config
        job.shared_large_status.ccd_metadata_list = [*dispatcher.ccd_metadata_dict.values()]

    await rpc_scatter(_save_job_metadata_rpc, job)
    await rpc_scatter(_save_ccd_distribution_config_rpc, job, dist_config)

    return GenerateSingleFitsTilesResult(
        ccd_metadata_list=[*dispatcher.ccd_metadata_dict.values()],
        ccd_profiles=dispatcher.build_ccd_profiles(),
        generator_profiles=dispatcher.build_generator_profiles(),
    )


async def _handle_generator_message(
    data: ProgressMessage | CompletedMessage | ErrorMessage,
    job: Job,
    dispatcher: CcdDispatcher,
    generator: GeneratorInfo,
    ws: aiohttp.ClientWebSocketResponse,
) -> None:
    """Generatorからのメッセージを処理"""
    match data:
        case ProgressMessage(ccd_name=ccd_name, progress=progress):
            if progress is not None:
                async with job.watcher.watch_status():
                    job.status.generate_single_fits_tiles[ccd_name] = progress

        case CompletedMessage(ccd_name=ccd_name, image_stat=image_stat, amps=amps, bbox=bbox):
            metadata = CcdMetadata(
                ccd_name=ccd_name,
                image_stat=image_stat,  # type: ignore
                amps=amps,  # type: ignore
                bbox=bbox,  # type: ignore
            )
            await dispatcher.on_ccd_completed(ccd_name, metadata, generator.id)
            logger.info(f"CCD {ccd_name} completed from {generator.id}, total: {len(dispatcher.ccd_metadata_dict)}/{len(dispatcher._ccd_refs)}")

            # 追加CCD割り当て
            next_ccd = await dispatcher.get_next_ccd(generator.id)
            if next_ccd is not None:
                await ws.send_bytes(pickle.dumps(AssignCcdMessage(ccd_ref=next_ccd)))
            elif not dispatcher.all_completed.is_set():
                # 追加CCDがない場合でも、Generatorが消失して再割り当てが発生する可能性がある
                # ccd_availableイベントを待つタスクを起動
                async def wait_and_assign():
                    ccd_ref = await _wait_for_next_ccd(dispatcher, generator.id)
                    if ccd_ref is not None:
                        await ws.send_bytes(pickle.dumps(AssignCcdMessage(ccd_ref=ccd_ref)))
                    # else: all_completedの場合、メインループ側でend signalを送信する
                asyncio.create_task(wait_and_assign())

        case ErrorMessage(ccd_name=ccd_name, error=error):
            logger.error(f"Generator {generator.id} error for CCD {ccd_name}: {error}")


async def _wait_for_next_ccd(dispatcher: CcdDispatcher, generator_id: GeneratorId) -> CcdDataRef | None:
    """
    次のCCDが利用可能になるまで待機する。

    Phase 2のresubmit対象がないときに、Generator消失によるCCD再割り当てを待つ。
    全CCDが完了した場合はNoneを返す。
    """
    while True:
        if dispatcher.all_completed.is_set():
            return None
        ccd_ref = await dispatcher.get_next_ccd(generator_id)
        if ccd_ref is not None:
            return ccd_ref
        # ConditionでCCD再割り当て通知を待つ（タイムアウト付き）
        try:
            async with dispatcher.ccd_available_condition:
                await asyncio.wait_for(dispatcher.ccd_available_condition.wait(), timeout=5.0)
        except asyncio.TimeoutError:
            pass  # タイムアウト後に再度チェック


def _save_job_metadata_rpc(job: Job) -> None:
    """ジョブのメタデータをローカルストレージに保存。"""
    job.local_storage.metadata.save()


def _save_ccd_distribution_config_rpc(job: Job, dist_config: CcdDistributionConfig) -> None:
    """CCD とジェネレータの対応関係をローカルストレージに保存。"""
    job.local_storage.ccd_distribution_config.save(dist_config)
