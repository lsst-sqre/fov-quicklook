"""
CCD処理用WebSocket API

CoordinatorからのCCD割り当てを受け、パイプラインで処理し、
進捗・完了をリアルタイムに返す。
"""

import asyncio
import pickle
import time
import traceback
from collections.abc import Generator
from typing import Any

import quicklook.mylogging
from fastapi import WebSocket, WebSocketDisconnect
from starlette.websockets import WebSocketState

from quicklook.config import config
from quicklook.generator.generate_single_fits_tiles import (
    CcdMetadata,
    GenerateSingleFitsTilesProgress,
    generate_single_fits_tiles_pipeline,
)
from quicklook.job.job import Job
from quicklook.types import CcdDataRef

from .ccd_processing_protocol import (
    AssignCcdMessage,
    CompletedMessage,
    ErrorMessage,
    GeneratorMessage,
    InitJobMessage,
    ProgressMessage,
)

logger = quicklook.mylogging.getLogger(__name__)


def validate_job_cache_version(job: Job) -> None:
    expected_version = config.tile_cache_schema_version
    if job.cache_version != expected_version:
        raise RuntimeError(
            f"Cache version mismatch: controller={job.cache_version}, generator={expected_version}"
        )


async def websocket_generate_tiles_raw(websocket: WebSocket) -> None:
    """
    CCD処理用WebSocketエンドポイント（生WebSocket版）

    最初のメッセージでJobオブジェクトを受け取り、
    その後CCDの割り当てを受けてパイプラインで処理する。

    プロトコル:
    1. Coordinator → Generator: InitJobMessage (pickle) でJobを送信
    2. Coordinator → Generator: AssignCcdMessage (pickle) でCCDを割り当て
    3. Generator → Coordinator: ProgressMessage | CompletedMessage | ErrorMessage (pickle)
    4. 終了: AssignCcdMessage(ccd_ref=None) または WebSocket切断

    Args:
        websocket: FastAPI WebSocket
    """
    await websocket.accept()

    # 最初のメッセージでJobを受け取る
    try:
        init_data = await websocket.receive_bytes()
        init_msg = pickle.loads(init_data)
        if not isinstance(init_msg, InitJobMessage) or init_msg.job is None:
            logger.error("First message must be InitJobMessage with job")
            await websocket.close(code=1002, reason="Expected InitJobMessage")
            return
        job = init_msg.job
        validate_job_cache_version(job)
        logger.info(f"WebSocket initialized for job {job.id}")
    except Exception as e:
        logger.error(f"Error receiving InitJobMessage: {e}")
        if websocket.client_state == WebSocketState.CONNECTED:
            await websocket.send_bytes(pickle.dumps(ErrorMessage(ccd_name=None, error=str(e))))
        await websocket.close(code=1002, reason="Failed to receive job")
        return

    # パイプライン状態
    ccd_queue: asyncio.Queue[CcdDataRef | None] = asyncio.Queue()
    cancel_event = asyncio.Event()

    async def receive_assignments() -> None:
        """Coordinatorからの割り当てを受信"""
        try:
            while not cancel_event.is_set():
                try:
                    data = await asyncio.wait_for(websocket.receive_bytes(), timeout=1.0)
                except asyncio.TimeoutError:
                    continue
                msg = pickle.loads(data)
                if isinstance(msg, AssignCcdMessage):
                    if msg.ccd_ref is None:
                        logger.info(f"Received end signal for job {job.id}")
                        # 終了シグナル
                        break
                    logger.info(f"Received CCD assignment: {msg.ccd_ref.ccd} for job {job.id}")
                    await ccd_queue.put(msg.ccd_ref)
                elif msg.type == "cancel":
                    cancel_event.set()
                    break
        except WebSocketDisconnect:
            logger.debug(f"WebSocket disconnected for job {job.id}")
            cancel_event.set()
        except Exception as e:
            logger.error(f"Error receiving assignments: {e}")
            cancel_event.set()
        finally:
            await ccd_queue.put(None)  # パイプライン終了シグナル

    async def run_pipeline() -> None:
        """パイプライン処理を実行"""
        loop = asyncio.get_running_loop()
        try:
            await asyncio.to_thread(
                _run_pipeline_sync,
                job,
                ccd_queue,
                cancel_event,
                loop,
                websocket,
            )
        except Exception as e:
            logger.error(f"Pipeline error: {e}\n{traceback.format_exc()}")
            await _send_generator_message(websocket, ErrorMessage(ccd_name=None, error=str(e)))
        finally:
            cancel_event.set()  # receive_assignmentsも終了させる

    try:
        await asyncio.gather(
            receive_assignments(),
            run_pipeline(),
        )
    except Exception as e:
        logger.error(f"WebSocket handler error: {e}")
        try:
            await websocket.send_bytes(pickle.dumps(ErrorMessage(ccd_name=None, error=str(e))))
        except Exception:
            pass
    finally:
        try:
            await websocket.close()
        except Exception:
            pass


def _run_pipeline_sync(
    job: Job,
    ccd_queue: asyncio.Queue[CcdDataRef | None],
    cancel_event: asyncio.Event,
    loop: asyncio.AbstractEventLoop,
    websocket: WebSocket,
) -> None:
    """
    同期パイプライン処理

    既存の generate_single_fits_tiles_pipeline を使用し、
    asyncio.Queue を同期的にブリッジする。
    """

    def ccd_generator() -> Generator[CcdDataRef, None, None]:
        """asyncio.Queueから同期的にCCDを取得。

        coordinatorからのend signal (None) または cancel_event で終了する。
        idle timeoutは使わない: coordinatorが all_completed 時に end signal を
        送信するため、generator側でのタイムアウト判定は不要。
        """
        ccd_index = 0
        while not cancel_event.is_set():
            try:
                t_wait_start = time.monotonic()
                future = asyncio.run_coroutine_threadsafe(
                    asyncio.wait_for(ccd_queue.get(), timeout=1.0),
                    loop,
                )
                ccd_ref = future.result(timeout=2.0)
                t_wait_end = time.monotonic()
                if ccd_ref is None:
                    logger.info("ccd_generator: received end signal (None), yielded %d CCDs", ccd_index)
                    break
                ccd_index += 1
                logger.info(
                    "ccd_generator: yielding %s (index=%d, queue_wait=%.3fs)",
                    ccd_ref.ccd, ccd_index, t_wait_end - t_wait_start,
                )
                yield ccd_ref
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.warning(f"ccd_generator: exception {e}, breaking")
                break
        else:
            logger.info("ccd_generator: cancel_event is set, exiting after %d CCDs", ccd_index)

    # 既存パイプラインを使用
    for msg in generate_single_fits_tiles_pipeline(job, ccd_generator()):
        match msg:
            case GenerateSingleFitsTilesProgress(ccd_name=ccd_name, progress=progress):
                if cancel_event.is_set():
                    break
                _send_generator_message_sync(
                    websocket,
                    ProgressMessage(
                    ccd_name=ccd_name,
                    stage="generating",
                    progress=progress,
                    ),
                    loop=loop,
                )
            case CcdMetadata(ccd_name=ccd_name, image_stat=image_stat, amps=amps, bbox=bbox):
                # CcdMetadata は cancel_event に関係なく必ず送信する
                _send_generator_message_sync(
                    websocket,
                    CompletedMessage(
                        ccd_name=ccd_name,
                        image_stat=image_stat,
                        amps=amps,
                        bbox=bbox,
                    ),
                    loop=loop,
                )


async def _send_generator_message(websocket: WebSocket, msg: GeneratorMessage) -> None:
    if websocket.client_state != WebSocketState.CONNECTED:
        if isinstance(msg, CompletedMessage):
            logger.warning(f"send_results: WebSocket not connected, dropping CompletedMessage for {msg.ccd_name}")
        return

    if isinstance(msg, CompletedMessage):
        logger.info(f"send_results: sending CompletedMessage for {msg.ccd_name} over WebSocket")
    await websocket.send_bytes(pickle.dumps(msg))
    if isinstance(msg, CompletedMessage):
        logger.info(f"send_results: CompletedMessage for {msg.ccd_name} sent successfully")


def _send_generator_message_sync(
    websocket: WebSocket,
    msg: GeneratorMessage,
    *,
    loop: asyncio.AbstractEventLoop,
) -> None:
    future = asyncio.run_coroutine_threadsafe(_send_generator_message(websocket, msg), loop)
    future.result(timeout=30.0)
