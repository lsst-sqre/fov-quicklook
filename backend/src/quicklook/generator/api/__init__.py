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
from typing import Annotated

import numpy
from fastapi import Depends, FastAPI, Response
from fastapi.responses import StreamingResponse

from quicklook.config import config
from quicklook.coordinator.quicklookjob.tasks import GenerateTask, TransferTask
from quicklook.deps.visit_from_path import visit_from_path
from quicklook.generator.api.baseprocesshandler import BaseProcessHandler
from quicklook.generator.progress import GenerateProgress
from quicklook.generator.tilegenerate import run_generate
from quicklook.generator.tiletransfer import run_transfer
from quicklook.generator.generatorlocaldisk import generator_local_disk
from quicklook.types import CcdId, GenerateTaskResponse, TransferProgress, TransferTaskResponse, Visit
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
    if tile_generate_process0().available():
        yield tile_generate_process0()
    else:  # pragma: no cover
        with create_tile_generate_process() as p:
            yield p


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
            msg: TransferTaskResponse = q.get()
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
        ndarray2npybytes(generator_local_disk.get_tile_npy(visit, z, y, x)),
        media_type='application/npy',
    )


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
    generator_local_disk.delete_all_cache()


@app.delete('/quicklooks/{id}')
async def delete_quicklooks(
    visit: Annotated[Visit, Depends(visit_from_path)],
):
    generator_local_disk.delete_cache(visit)


@app.post('/kill')
async def kill():  # pragma: no cover
    os._exit(0)


def tile_generate_process_target(comm: Connection) -> None:
    while True:
        task: GenerateTask | None = comm.recv()
        if task is None:
            break
        try:
            run_generate(task, comm.send)
        except Exception as e:  # pragma: no cover
            traceback.print_exc()
            comm.send(e)
        finally:
            comm.send(None)


def tile_transfer_process_target(comm: Connection) -> None:
    while True:
        task: TransferTask | None = comm.recv()
        if task is None:
            break
        try:
            run_transfer(task, comm.send)
        except Exception as e:  # pragma: no cover
            traceback.print_exc()
            comm.send(e)
        finally:
            comm.send(None)
