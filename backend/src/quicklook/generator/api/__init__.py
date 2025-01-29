import logging
import queue
import threading
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated

import numpy
from fastapi import Depends, FastAPI, Response
from fastapi.responses import StreamingResponse

from quicklook.config import config
from quicklook.coordinator.tasks import GeneratorTask
from quicklook.deps.visit_from_path import visit_from_path
from quicklook.generator.api.tilegeneratorprocess import TileGeneratorProcess
from quicklook.types import CcdId, MessageFromGeneratorToCoordinator, Visit
from quicklook.utils.globalstack import GlobalStack
from quicklook.utils.lrudict import LRUDict
from quicklook.utils.message import encode_message
from quicklook.utils.numpyutils import ndarray2npybytes
from quicklook.utils.podstatus import pod_status

from .context import GeneratorContext

logger = logging.getLogger(f'uvicorn.{__name__}')
ctx = GeneratorContext()
tile_generator = TileGeneratorProcess()


@dataclass
class GeneratorRuntimeSettings:
    port: int
    stack = GlobalStack['GeneratorRuntimeSettings']()


GeneratorRuntimeSettings.stack.set_default(GeneratorRuntimeSettings(port=config.generator_port))


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with ctx.activate(GeneratorRuntimeSettings.stack.top.port):
        with tile_generator:
            yield


app = FastAPI(lifespan=lifespan)


@app.get('/healthz')
async def healthz():
    return {'status': 'ok'}


visit_ccd_names = LRUDict[Visit, set[str]](32)


@app.post("/quicklooks")
def create_quicklook(task: GeneratorTask):
    visit_ccd_names.set(task.visit, set(task.ccd_names))
    q = queue.Queue()

    def main():
        tile_generator.create_quicklook(task, on_update=q.put)

    def stream_task_updates():
        t = threading.Thread(target=main)
        t.start()
        while True:
            msg: MessageFromGeneratorToCoordinator = q.get()
            yield encode_message(msg)
            if msg is None:
                break
        t.join()

    return StreamingResponse(stream_task_updates())


@app.get('/quicklooks/{id}/tiles/{z}/{y}/{x}')
def get_tile(
    visit: Annotated[Visit, Depends(visit_from_path)],
    z: int,
    y: int,
    x: int,
):
    ccd_names = visit_ccd_names.get(visit)
    # ccd_names = visit_ccd_names.get(visit) & set(TileInfo.of(z, y, x).ccd_names)
    pool: numpy.ndarray | None = None
    for ccd_name in ccd_names:
        ccd_id = CcdId(visit, ccd_name)
        path = f'{config.tile_tmpdir}/{ccd_id.name}/{z}/{y}/{x}.npy'
        if not Path(path).exists():
            # こういうことはまれにある
            # TileInfo.ofの結果は不安定なので
            continue
        arr = numpy.load(path)
        if pool is None:
            pool = arr
        else:  # pragma: no cover
            pool += arr
    if pool is None:
        return numpy.zeros((config.tile_size, config.tile_size), dtype=numpy.float32)
    return Response(ndarray2npybytes(pool), media_type='application/npy')


@app.get('/quicklooks/{id}/fits_header/{ccd_name}')
def get_fits_header(
    visit: Annotated[Visit, Depends(visit_from_path)],
    ccd_name: str,
):
    ccd_id = CcdId(visit, ccd_name)
    outfile = Path(f'{config.fits_header_tmpdir}/{ccd_id.name}.json')
    if not outfile.exists():
        return
    # ファイルの内容はjsonであることが保証されている
    # 内容が大きいのでそのまま返す
    return Response(outfile.read_text(), media_type='application/json')


@app.get('/pod_status')
async def get_pod_status():
    return await pod_status()
