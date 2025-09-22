import fastapi
from fastapi.responses import StreamingResponse

from quicklook import rpc
from quicklook.comm.generator import router as comm_generator_router
from quicklook.utils.async_process_generator import run_async_process_generator

app = fastapi.FastAPI()


@app.get("/healthz")
async def route_healthz():
    return {"status": "ok"}


@app.post('/rpc')
async def route_rpc(request: fastapi.Request):
    return StreamingResponse(
        run_async_process_generator(_rpc_worker, await request.body()),
        media_type='application/octet-stream',
    )


def _rpc_worker(body: bytes):
    for progress in rpc.create_rpc_caller_endpoint(body):
        yield progress


app.include_router(comm_generator_router)
