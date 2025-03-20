import logging
import os
import queue
import threading
import traceback
from contextlib import asynccontextmanager, contextmanager
from dataclasses import dataclass
from functools import cache
from multiprocessing.connection import Connection
from pathlib import Path
from typing import Annotated, Callable, TypeVar

import numpy
from fastapi import Depends, FastAPI, HTTPException, Response
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from quicklook.config import config
from quicklook.coordinator.quicklookjob.tasks import GenerateTask, MergeTask, TransferTask
from quicklook.deps.visit_from_path import visit_from_path
from quicklook.generator.api.baseprocesshandler import BaseProcessHandler
from quicklook.generator.api.tilegenerate import run_generate
from quicklook.generator.api.tilemerge import run_merge
from quicklook.generator.api.tiletransfer import run_transfer
from quicklook.generator.generatorstorage import mergedtile_storage, tmptile_storage
from quicklook.generator.progress import GenerateProgress
from quicklook.mutableconfig import update_mutable_config
from quicklook.types import CcdId, GenerateTaskResponse, MergeProgress, MergeTaskResponse, TransferProgress, Visit
from quicklook.utils.globalstack import GlobalStack
from quicklook.utils.message import encode_message
from quicklook.utils.numpyutils import ndarray2npybytes
from quicklook.utils.podstatus import pod_status
from quicklook.utils.timeit import timeit

from .context import GeneratorContext

logger = logging.getLogger(f'uvicorn.{__name__}')
ctx = GeneratorContext()


@dataclass
class GeneratorRuntimeSettings:
    port: int
    stack = GlobalStack['GeneratorRuntimeSettings']()


GeneratorRuntimeSettings.stack.set_default(GeneratorRuntimeSettings(port=config.generator_port))


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with ctx.activate(GeneratorRuntimeSettings.stack.top.port):
        with tile_generate_process0():
            yield


app = FastAPI(lifespan=lifespan)


@app.get('/healthz')
async def healthz():
    return {'status': 'ok'}


@app.post("/quicklooks")
def create_quicklook(task: GenerateTask):
    q = queue.Queue()

    def main():
        with tile_generate_process() as p:
            logger.info(f'Create quicklook for {task}')
            with timeit(f'create_quicklook {task}'):
                p.execute_task(task, on_update=q.put)

    def stream_task_updates():
        t = threading.Thread(target=main)
        t.start()
        while True:
            msg: GenerateTaskResponse = q.get()
            yield encode_message(msg)
            if msg is None:
                break
        t.join()

    return StreamingResponse(stream_task_updates())


@cache
def tile_generate_process0():
    return create_tile_generate_process()


def create_tile_generate_process() -> BaseProcessHandler[GenerateTask, GenerateProgress]:
    return BaseProcessHandler[GenerateTask, GenerateProgress](process_target=tile_generate_process_target)


@contextmanager
def tile_generate_process():
    # process0だけは常に使い回す
    # multiprocessing.Poolの生成に時間がかかるので
    if tile_generate_process0().available():
        yield tile_generate_process0()
    else:  # pragma: no cover
        with create_tile_generate_process() as p:
            yield p


@app.post('/quicklooks/merge')
def merge_quicklook(task: MergeTask):
    logger.info(f'Merge quicklook for {task}')

    q = queue.Queue()

    def main():
        with tile_merge_process() as p:
            p.execute_task(task, on_update=q.put)

    def stream_task_updates():
        t = threading.Thread(target=main)
        t.start()
        while True:
            msg: MergeTaskResponse = q.get()
            yield encode_message(msg)
            if msg is None:
                break
        t.join()

    return StreamingResponse(stream_task_updates())


def tile_merge_process():
    return BaseProcessHandler[MergeTask, MergeProgress](process_target=tile_merge_process_target)


@app.post('/quicklooks/transfer')
def transfer_quicklook(task: TransferTask):
    logger.info(f'Transfer quicklook for {task}')

    q = queue.Queue()

    def main():
        with tile_transfer_process() as p:
            p.execute_task(task, on_update=q.put)

    def stream_task_updates():
        t = threading.Thread(target=main)
        t.start()
        while True:
            msg: MergeTaskResponse = q.get()
            yield encode_message(msg)
            if msg is None:
                break
        t.join()

    return StreamingResponse(stream_task_updates())


def tile_transfer_process():
    return BaseProcessHandler[TransferTask, TransferProgress](process_target=tile_transfer_process_target)


@app.get('/quicklooks/{id}/tiles/{z}/{y}/{x}')
def get_tile(
    visit: Annotated[Visit, Depends(visit_from_path)],
    z: int,
    y: int,
    x: int,
):
    return Response(
        ndarray2npybytes(tmptile_storage.get_tile_npy(visit, z, y, x)),
        media_type='application/npy',
    )


@app.get('/quicklooks/{id}/merged-tiles/{z}/{y}/{x}')
def get_merged_tile(
    visit: Annotated[Visit, Depends(visit_from_path)],
    z: int,
    y: int,
    x: int,
):
    try:
        return Response(
            mergedtile_storage.get_tile_data(visit, z, y, x),
            media_type='application/npy+zstd',
        )
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail='Tile not found')


@app.get('/quicklooks/{id}/fits_header/{ccd_name}')
def get_fits_header(
    visit: Annotated[Visit, Depends(visit_from_path)],
    ccd_name: str,
):
    ccd_id = CcdId(visit, ccd_name)
    outfile = Path(f'{config.fits_header_tmpdir}/{ccd_id.name}.json')
    if not outfile.exists():  # pragma: no cover
        return
    # ファイルの内容はjsonであることが保証されている
    # 内容が大きいのでそのまま返す
    return Response(outfile.read_bytes(), media_type='application/json')


@app.get('/pod_status')
async def get_pod_status():
    return await pod_status()


@app.delete('/quicklooks/*')
async def delete_all_quicklooks():
    tmptile_storage.delete_all()


@app.delete('/quicklooks/{id}')
async def delete_quicklooks(
    visit: Annotated[Visit, Depends(visit_from_path)],
):
    tmptile_storage.delete(visit)



if config.environment == 'test':
    class MutableConfigUpdate(BaseModel):
        new: dict

    @app.post(f"/mutable-config")
    async def config_endpoint(params: MutableConfigUpdate):
        update_mutable_config(params.new)


@app.post('/kill')
async def kill():  # pragma: no cover
    os._exit(0)


T = TypeVar('T')
P = TypeVar('P')


def create_process_target(runner_func: Callable[[T, Callable[[P | Exception | None], None]], None]) -> Callable[[Connection], None]:
    def process_target(comm: Connection) -> None:
        while True:
            task: T | None = comm.recv()
            if task is None:
                break
            try:
                runner_func(task, comm.send)
            except Exception as e:  # pragma: no cover
                traceback.print_exc()
                comm.send(e)
            finally:
                comm.send(None)

    return process_target


tile_generate_process_target = create_process_target(run_generate)
tile_merge_process_target = create_process_target(run_merge)
tile_transfer_process_target = create_process_target(run_transfer)
