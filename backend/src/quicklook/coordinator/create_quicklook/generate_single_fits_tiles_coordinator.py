"""
Generate Single FITS Tiles: Coordinator側実装

WebSocket API方式によるFITSタイル生成。
各Generatorに対してWebSocket接続を確立し、動的にCCDを割り当てながら処理を行う。
"""

import asyncio
import pickle
import time
from dataclasses import dataclass, field

import aiohttp

import quicklook.mylogging
from quicklook.comm.coordinator import (
    get_available_generators,
    add_on_generator_registered_callback,
    remove_on_generator_registered_callback,
    add_on_generator_removed_callback,
    remove_on_generator_removed_callback,
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

from .ccd_dispatcher import CcdDispatcher

logger = quicklook.mylogging.getLogger(__name__)


def _merge_generate_progress(existing: Progress | None, incoming: Progress) -> Progress:
    """Keep per-CCD progress monotonic when the same CCD is resubmitted."""
    if existing is None:
        return Progress(total=incoming.total, count=incoming.count)

    existing_total = existing.total or 1
    incoming_total = incoming.total or 1
    existing_ratio = existing.count / existing_total
    incoming_ratio = incoming.count / incoming_total

    if incoming_ratio > existing_ratio:
        return Progress(total=incoming.total, count=incoming.count)
    if incoming_ratio < existing_ratio:
        return Progress(total=existing.total, count=existing.count)

    if incoming.count >= existing.count:
        return Progress(total=incoming.total, count=incoming.count)
    return Progress(total=existing.total, count=existing.count)


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
    ccd_refs = sorted(ccd_refs, key=lambda ref: ref.ccd)
    initial_generators = dict(get_available_generators())
    if not initial_generators:
        raise RuntimeError("No generators available")

    known_generators = dict(initial_generators)
    generator_list = list(initial_generators.values())
    dispatcher = CcdDispatcher(ccd_refs)
    max_concurrent_ccds = config.generator_max_concurrent_ccds_per_job
    max_worker_connect_retries = 3
    worker_connect_retry_interval = 2.0

    async def _run_worker_session(generator: GeneratorInfo, initial_ccd: CcdDataRef | None = None) -> None:
        """
        GeneratorへのWebSocket接続を確立し、CCD処理ループを実行する。
        接続失敗時は呼び出し元でリトライする。

        initial_ccd: resubmitフローで事前に取得済みのCCD。
                     指定時はこのCCDを初期バッチの最初に含める。
        """
        ws_url = f"{generator.ws_url}/jobs/{job.id}/generate-tiles"
        logger.info(f"Worker connecting to {ws_url}")

        timeout = aiohttp.ClientTimeout(total=None, connect=10, sock_connect=10, sock_read=None)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.ws_connect(ws_url, heartbeat=5.0) as ws:
                logger.info(f"Connected to generator {generator.id}")
                dispatcher.record_generator_start(generator.id)

                # 最初にJobオブジェクトを送信
                await ws.send_bytes(pickle.dumps(InitJobMessage(job=job)))
                logger.debug(f"Sent InitJobMessage to generator {generator.id}")

                # 初期バッチ割り当て
                has_initial_batch = False

                # resubmitフローで事前取得したCCDがある場合、最初に割り当て
                if initial_ccd is not None:
                    logger.info(f"Assigning pre-fetched resubmit CCD {initial_ccd.ccd} to generator {generator.id}")
                    await _record_assigned_ccd(job, initial_ccd.ccd)
                    await ws.send_bytes(pickle.dumps(AssignCcdMessage(ccd_ref=initial_ccd)))
                    has_initial_batch = True

                remaining_slots = max_concurrent_ccds - (1 if initial_ccd is not None else 0)
                for _ in range(remaining_slots):
                    ccd_ref = await dispatcher.get_next_ccd(generator.id)
                    if ccd_ref is not None:
                        logger.debug(f"Assigning CCD {ccd_ref.ccd} to generator {generator.id}")
                        await _record_assigned_ccd(job, ccd_ref.ccd)
                        await ws.send_bytes(pickle.dumps(AssignCcdMessage(ccd_ref=ccd_ref)))
                        has_initial_batch = True

                if not has_initial_batch:
                    # 初期バッチがない場合、Phase 2での参加を待つ
                    ccd_ref = await _wait_for_next_ccd(dispatcher, generator.id)
                    if ccd_ref is None:
                        await ws.send_bytes(pickle.dumps(AssignCcdMessage(ccd_ref=None)))
                        return
                    await _record_assigned_ccd(job, ccd_ref.ccd)
                    await ws.send_bytes(pickle.dumps(AssignCcdMessage(ccd_ref=ccd_ref)))

                logger.info(f"Initial batch sent to generator {generator.id}, waiting for responses")
                end_signal_sent = False
                pending_wait_tasks: list[asyncio.Task[None]] = []

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
                                data, job, dispatcher, generator, ws,
                                pending_wait_tasks,
                            )

                        elif msg.type == aiohttp.WSMsgType.CLOSED:
                            logger.info(f"WebSocket closed by generator {generator.id}")
                            break
                        elif msg.type == aiohttp.WSMsgType.ERROR:
                            logger.error(f"WebSocket error from generator {generator.id}: {ws.exception()}")
                            break
                finally:
                    completion_task.cancel()
                    for t in pending_wait_tasks:
                        t.cancel()
                    for t in [completion_task, *pending_wait_tasks]:
                        try:
                            await t
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
        pending_resubmit_ccd: CcdDataRef | None = None
        try:
            while not dispatcher.all_completed.is_set():
                try:
                    await _run_worker_session(current_generator, initial_ccd=pending_resubmit_ccd)
                    pending_resubmit_ccd = None
                    consecutive_failures = 0

                    if dispatcher.all_completed.is_set():
                        return

                    # generatorがまだ利用可能か確認
                    available = get_available_generators()
                    if generator_id not in available:
                        # Generator消失: on_generator_lostを呼んでresubmit対象にする
                        logger.info(f"Generator {generator_id} no longer available after session")
                        await dispatcher.on_generator_lost(generator_id)
                        return

                    # 正常終了後、resubmit可能なCCDが出るまで待機
                    ccd_ref = await _wait_for_next_ccd(dispatcher, generator_id)
                    if ccd_ref is None:
                        return  # 全完了

                    # resubmit用の新しいセッションに入る前にgenerator情報を更新
                    available = get_available_generators()
                    if generator_id not in available:
                        logger.info(f"Generator {generator_id} no longer available before resubmit session")
                        await dispatcher.return_unassigned_ccd(ccd_ref)
                        return
                    current_generator = available[generator_id]
                    known_generators[generator_id] = current_generator
                    pending_resubmit_ccd = ccd_ref
                    logger.info(f"Worker {generator_id} starting new session for resubmit CCD {ccd_ref.ccd}")

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
                        known_generators[generator_id] = current_generator
                        logger.info(f"Retrying with updated generator info: {current_generator.ws_url}")
                    else:
                        logger.warning(f"Generator {generator_id} no longer available, stopping worker")
                        break

                except asyncio.CancelledError:
                    raise
                except Exception as e:
                    logger.error(f"Worker error for generator {generator_id}: {e}")
                    break  # 予期しないエラーはリトライしない
        finally:
            if pending_resubmit_ccd is not None:
                await dispatcher.return_unassigned_ccd(pending_resubmit_ccd)
            dispatcher.record_generator_end(generator_id)
            await dispatcher.on_generator_lost(generator_id)

    # 全workerを起動
    active_worker_generator_ids: set[GeneratorId] = {g.id for g in generator_list}
    worker_tasks = [asyncio.create_task(worker(g)) for g in generator_list]

    # 新しいgeneratorが登録されたときにworkerを動的に追加するコールバック
    def on_new_generator(generator_info: GeneratorInfo) -> None:
        known_generators[generator_info.id] = generator_info
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

    # Generatorが削除されたときにdispatcherのon_generator_lostを即座に呼ぶコールバック
    # これにより、healthcheck失敗やkill_random_generatorによる削除時に
    # workerのWebSocket切断を待たずに即座にresubmitが開始される
    def on_generator_removed(generator_info: GeneratorInfo) -> None:
        if dispatcher.all_completed.is_set():
            return
        logger.info(f"Generator {generator_info.id} removed, triggering on_generator_lost")
        asyncio.create_task(dispatcher.on_generator_lost(generator_info.id))

    add_on_generator_removed_callback(on_generator_removed)

    timeout_seconds = config.generate_single_fits_tiles_timeout_seconds
    try:
        # 全CCD完了を待機（タイムアウト付き）
        await asyncio.wait_for(dispatcher.all_completed.wait(), timeout=timeout_seconds)
    except asyncio.TimeoutError:
        completed_ccds = set(dispatcher.ccd_metadata_dict.keys())
        all_ccds = {ref.ccd for ref in ccd_refs}
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
        remove_on_generator_removed_callback(on_generator_removed)
        # 残存workerをキャンセル
        for task in worker_tasks:
            if not task.done():
                task.cancel()
        await asyncio.gather(*worker_tasks, return_exceptions=True)

    if len(dispatcher.ccd_metadata_dict) != len(ccd_refs):
        raise RuntimeError(
            f"Not all CCDs processed: got {len(dispatcher.ccd_metadata_dict)}/{len(ccd_refs)} metadata"
        )

    generator_ids = sorted(set(dispatcher.ccd_generator_map.values()))
    missing_generator_ids = [gid for gid in generator_ids if gid not in known_generators]
    if missing_generator_ids:
        raise RuntimeError(f"Missing generator info for completed CCDs: {missing_generator_ids}")
    job_generators = {gid: known_generators[gid] for gid in generator_ids}

    dist_config = CcdDistributionConfig(dispatcher.ccd_generator_map, job_generators)
    async with job.watcher.notify_shared_large_status():
        job.shared_large_status.dist_config = dist_config
        job.shared_large_status.ccd_metadata_list = [*dispatcher.ccd_metadata_dict.values()]

    await rpc_scatter(_save_job_metadata_rpc, job, generators=job_generators)
    await rpc_scatter(_save_ccd_distribution_config_rpc, job, dist_config, generators=job_generators)

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
    pending_wait_tasks: list[asyncio.Task[None]],
) -> None:
    """Generatorからのメッセージを処理"""
    match data:
        case ProgressMessage(ccd_name=ccd_name, progress=progress):
            if progress is not None:
                async with job.watcher.watch_status():
                    current = job.status.generate_single_fits_tiles.get(ccd_name)
                    job.status.generate_single_fits_tiles[ccd_name] = _merge_generate_progress(
                        current,
                        progress,
                    )

        case CompletedMessage(ccd_name=ccd_name, image_stat=image_stat, amps=amps, bbox=bbox, wcs=wcs):
            metadata = CcdMetadata(
                ccd_name=ccd_name,
                image_stat=image_stat,  # type: ignore
                amps=amps,  # type: ignore
                bbox=bbox,  # type: ignore
                wcs=wcs,
            )
            await dispatcher.on_ccd_completed(ccd_name, metadata, generator.id)

            # 追加CCD割り当て
            next_ccd = await dispatcher.get_next_ccd(generator.id)
            if next_ccd is not None:
                await _record_assigned_ccd(job, next_ccd.ccd)
                await ws.send_bytes(pickle.dumps(AssignCcdMessage(ccd_ref=next_ccd)))
            elif not dispatcher.all_completed.is_set():
                # 追加CCDがない場合でも、Generatorが消失して再割り当てが発生する可能性がある
                # ccd_availableイベントを待つタスクを起動
                async def wait_and_assign():
                    ccd_ref = await _wait_for_next_ccd(dispatcher, generator.id)
                    if ccd_ref is not None:
                        try:
                            await _record_assigned_ccd(job, ccd_ref.ccd)
                            await ws.send_bytes(pickle.dumps(AssignCcdMessage(ccd_ref=ccd_ref)))
                        except Exception as e:
                            # WebSocketが閉じられている場合、worker()レベルの
                            # resubmitループで処理されるため、ここではCCDを返却する
                            logger.debug(f"Failed to assign resubmit CCD {ccd_ref.ccd} to {generator.id}: {e}")
                            await dispatcher.return_unassigned_ccd(ccd_ref)
                    # else: all_completedの場合、メインループ側でend signalを送信する
                task = asyncio.create_task(wait_and_assign())
                pending_wait_tasks.append(task)

        case ErrorMessage(ccd_name=ccd_name, error=error):
            logger.error(f"Generator {generator.id} error for CCD {ccd_name}: {error}")
            raise RuntimeError(f"Generator {generator.id} error for CCD {ccd_name}: {error}")


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
                await asyncio.wait_for(dispatcher.ccd_available_condition.wait(), timeout=1.0)
        except asyncio.TimeoutError:
            pass  # タイムアウト後に再度チェック


async def _record_assigned_ccd(job: Job, ccd_name: CcdName) -> None:
    async with job.watcher.watch_status():
        job.status.generate_single_fits_tiles.setdefault(ccd_name, Progress(total=4, count=0))


def _save_job_metadata_rpc(job: Job) -> None:
    """ジョブのメタデータをローカルストレージに保存。"""
    job.local_storage.metadata.save()


def _save_ccd_distribution_config_rpc(job: Job, dist_config: CcdDistributionConfig) -> None:
    """CCD とジェネレータの対応関係をローカルストレージに保存し、敗者タイルを削除。"""
    job.local_storage.ccd_distribution_config.save(dist_config)
    job.local_storage.single_fits_tile.remove_non_owned_tiles()
