import logging
import os
from contextlib import asynccontextmanager, contextmanager
from dataclasses import dataclass
from multiprocessing.connection import Connection
from pathlib import Path
from typing import Annotated, Callable, TypeVar

from fastapi import Depends, FastAPI, HTTPException, Response
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from quicklook.config import config
from quicklook.coordinator.quicklookjob.tasks import GenerateTask, MergeTask, TransferTask
from quicklook.deps.visit_from_path import visit_from_path
from quicklook.generator.api.processcomm import Connection, spawn_process_with_comm
from quicklook.generator.api.tilegenerate import run_generate
from quicklook.generator.api.tilemerge import run_merge
from quicklook.generator.api.tiletransfer import run_transfer
from quicklook.generator.generatorstorage import mergedtile_storage, tmptile_storage
from quicklook.mutableconfig import update_mutable_config
from quicklook.types import CcdId, GenerateTaskResponse, MergeTaskResponse, TransferProgress, Visit
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
        yield


app = FastAPI(lifespan=lifespan)


@app.get('/healthz')
async def healthz():
    return {'status': 'ok'}


@app.post("/quicklooks")
def create_quicklook(task: GenerateTask):
    def stream_task_updates():
        logger.info(f'Generate quicklook for {task}')
        with timeit(f'Generate quicklook for {task}'):
            with spawn_process_with_comm(make_process_target(run_generate, task)) as p:
                while True:
                    msg: GenerateTaskResponse = p.comm.recv()
                    yield encode_message(msg)
                    if msg is None:
                        break

    return StreamingResponse(stream_task_updates())


@app.post('/quicklooks/merge')
def merge_quicklook(task: MergeTask):
    def stream_task_updates():
        logger.info(f'Merge quicklook for {task}')
        with timeit(f'Merge quicklook for {task}'):
            with spawn_process_with_comm(make_process_target(run_merge, task)) as p:
                while True:
                    msg: MergeTaskResponse = p.comm.recv()
                    yield encode_message(msg)
                    if msg is None:
                        break

    return StreamingResponse(stream_task_updates())


@app.post('/quicklooks/transfer')
def transfer_quicklook(task: TransferTask):
    def stream_task_updates():
        logger.info(f'Transfer quicklook for {task}')
        with timeit(f'Transfer quicklook for {task}'):
            with spawn_process_with_comm(make_process_target(run_transfer, task)) as p:
                while True:
                    msg: TransferProgress = p.comm.recv()
                    yield encode_message(msg)
                    if msg is None:
                        break

    return StreamingResponse(stream_task_updates())


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
            mergedtile_storage.get_compressed_tile_data(visit, z, y, x),
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
    return await pod_status(storage_dirs=[config.tile_tmpdir, config.tile_merged_dir])


@app.delete('/quicklooks/*')
async def delete_all_quicklooks():
    tmptile_storage.delete_all()
    mergedtile_storage.delete_all()


class DeleteQuicklookParams(BaseModel):
    tmp_tile: bool = True
    merged_tile: bool = True


@app.delete('/quicklooks/{id}')
async def delete_quicklooks(
    visit: Annotated[Visit, Depends(visit_from_path)],
    params: DeleteQuicklookParams,
):
    if params.tmp_tile:
        tmptile_storage.delete(visit)
    if params.merged_tile:
        mergedtile_storage.delete(visit)


if config.environment == 'test':

    class MutableConfigUpdate(BaseModel):
        new: dict

    @app.post(f"/mutable-config")
    async def config_endpoint(params: MutableConfigUpdate):
        update_mutable_config(params.new)


T = TypeVar('T')
P = TypeVar('P')


def make_process_target(
    runner_func: Callable[
        [T, Callable[[P], None]],
        None,
    ],
    task: T,
) -> Callable[[Connection], None]:
    def process_target(comm: Connection):
        try:
            runner_func(task, comm.send)
        except Exception as e:
            logger.exception(f'Error in process: {e}')
            comm.send(e)
        finally:
            comm.send(None)

    return process_target
