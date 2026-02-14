"""
CCD処理用WebSocket API

CoordinatorからのCCD割り当てを受け、パイプラインで処理し、
進捗・完了をリアルタイムに返す。
"""

import asyncio
import pickle
import traceback
from collections.abc import Generator
from typing import Any

import quicklook.mylogging
from fastapi import WebSocket, WebSocketDisconnect
from starlette.websockets import WebSocketState

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
        logger.info(f"WebSocket initialized for job {job.id}")
    except Exception as e:
        logger.error(f"Error receiving InitJobMessage: {e}")
        await websocket.close(code=1002, reason="Failed to receive job")
        return

    # パイプライン状態
    ccd_queue: asyncio.Queue[CcdDataRef | None] = asyncio.Queue()
    result_queue: asyncio.Queue[GeneratorMessage | None] = asyncio.Queue()
    cancel_event = asyncio.Event()

    async def receive_assignments() -> None:
        """Coordinatorからの割り当てを受信"""
        try:
            while not cancel_event.is_set():
                data = await websocket.receive_bytes()
                msg = pickle.loads(data)
                if isinstance(msg, AssignCcdMessage):
                    if msg.ccd_ref is None:
                        logger.info(f"Received end signal for job {job.id}")
                        # 終了シグナル
                        break
                    logger.info(f"Received CCD assignment: {msg.ccd_ref.ccd_name} for job {job.id}")
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

    async def send_results() -> None:
        """処理結果をCoordinatorへ送信"""
        try:
            while not cancel_event.is_set():
                msg = await result_queue.get()
                if msg is None:
                    break
                if isinstance(msg, CompletedMessage):
                    logger.info(f"send_results: sending CompletedMessage for {msg.ccd_name} over WebSocket")
                if websocket.client_state == WebSocketState.CONNECTED:
                    await websocket.send_bytes(pickle.dumps(msg))
                    if isinstance(msg, CompletedMessage):
                        logger.info(f"send_results: CompletedMessage for {msg.ccd_name} sent successfully")
                else:
                    if isinstance(msg, CompletedMessage):
                        logger.warning(f"send_results: WebSocket not connected, dropping CompletedMessage for {msg.ccd_name}")
        except WebSocketDisconnect:
            logger.warning("send_results: WebSocket disconnected")
        except Exception as e:
            logger.error(f"Error sending results: {e}")

    async def run_pipeline() -> None:
        """パイプライン処理を実行"""
        loop = asyncio.get_running_loop()
        try:
            await asyncio.to_thread(
                _run_pipeline_sync,
                job,
                ccd_queue,
                result_queue,
                cancel_event,
                loop,
            )
        except Exception as e:
            logger.error(f"Pipeline error: {e}\n{traceback.format_exc()}")
            await result_queue.put(ErrorMessage(ccd_name=None, error=str(e)))
        finally:
            await result_queue.put(None)  # 送信ループ終了シグナル

    try:
        await asyncio.gather(
            receive_assignments(),
            send_results(),
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
    result_queue: asyncio.Queue[GeneratorMessage | None],
    cancel_event: asyncio.Event,
    loop: asyncio.AbstractEventLoop,
) -> None:
    """
    同期パイプライン処理

    既存の generate_single_fits_tiles_pipeline を使用し、
    asyncio.Queue を同期的にブリッジする。
    """

    def ccd_generator() -> Generator[CcdDataRef, None, None]:
        """asyncio.Queueから同期的にCCDを取得"""
        while not cancel_event.is_set():
            try:
                future = asyncio.run_coroutine_threadsafe(
                    asyncio.wait_for(ccd_queue.get(), timeout=1.0),
                    loop,
                )
                ccd_ref = future.result(timeout=2.0)
                if ccd_ref is None:
                    break
                yield ccd_ref
            except asyncio.TimeoutError:
                continue
            except Exception:
                break

    def put_result(msg: GeneratorMessage) -> None:
        """結果キューにメッセージを追加（同期的に完了を待つ）"""
        if isinstance(msg, CompletedMessage):
            logger.info(f"put_result: sending CompletedMessage for {msg.ccd_name}")
        future = asyncio.run_coroutine_threadsafe(result_queue.put(msg), loop)
        future.result(timeout=30.0)  # 結果喪失を防ぐため完了を待つ
        if isinstance(msg, CompletedMessage):
            logger.info(f"put_result: CompletedMessage for {msg.ccd_name} queued successfully")

    # 既存パイプラインを使用
    for msg in generate_single_fits_tiles_pipeline(job, ccd_generator()):
        match msg:
            case GenerateSingleFitsTilesProgress(ccd_name=ccd_name, progress=progress):
                if cancel_event.is_set():
                    break
                put_result(ProgressMessage(
                    ccd_name=ccd_name,
                    stage="generating",
                    progress=progress,
                ))
            case CcdMetadata(ccd_name=ccd_name, image_stat=image_stat, amps=amps, bbox=bbox):
                # CcdMetadata は cancel_event に関係なく必ず送信する
                put_result(CompletedMessage(
                    ccd_name=ccd_name,
                    image_stat=image_stat,
                    amps=amps,
                    bbox=bbox,
                ))
