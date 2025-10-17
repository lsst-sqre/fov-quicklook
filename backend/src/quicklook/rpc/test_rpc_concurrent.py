# RPC module concurrency tests

import asyncio
import multiprocessing as mp
import queue
from typing import Generator

import pytest
import uvicorn
from fastapi import FastAPI, WebSocket

from quicklook.comm.generator import set_generator_id_for_test
from quicklook.rpc import Rpc, create_rpc_endpoint, rpc_lifespan
from quicklook.rpc.queue import RpcQueue


class _QueueEndSentinel:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __reduce__(self):
        return (self.__class__, ())


_QUEUE_END = _QueueEndSentinel()


def _process_item_double(x: int) -> int:
    """Helper function for multiprocessing.Pool (must be at module level)"""
    return x * 2


def _process_item_triple(x: int) -> int:
    """Helper function for multiprocessing.Pool (must be at module level)"""
    return x * 3


def heavy_computation_with_pool(items: list[int]) -> list[int]:
    with mp.Pool(4) as pool:
        results = pool.map(_process_item_double, items)

    return results


def queue_based_computation(q: queue.Queue) -> Generator[int, None, None]:
    batch = []
    while True:
        item = q.get()
        if isinstance(item, _QueueEndSentinel):
            break
        batch.append(item)

        if len(batch) >= 4:
            with mp.Pool(2) as pool:
                results = pool.map(_process_item_triple, batch)
            for result in results:
                yield result
            batch = []

    if batch:
        with mp.Pool(2) as pool:
            results = pool.map(_process_item_triple, batch)
        for result in results:
            yield result


@pytest.fixture
async def rpc_app():
    app = FastAPI(lifespan=rpc_lifespan)

    @app.websocket("/rpc")
    async def rpc_endpoint(ws: WebSocket):
        await create_rpc_endpoint(app, ws)

    return app


@pytest.fixture
async def rpc_server(rpc_app):
    with set_generator_id_for_test():
        config = uvicorn.Config(rpc_app, host="127.0.0.1", port=8766, log_level="error")
        server = uvicorn.Server(config)

        task = asyncio.create_task(server.serve())
        await asyncio.sleep(0.5)

        yield "ws://127.0.0.1:8766/rpc"

        server.should_exit = True
        await task


async def test_high_concurrency_with_pool(rpc_server):
    tasks = []
    for i in range(8):
        items = list(range(i * 10, (i + 1) * 10))
        rpc = Rpc(rpc_server, heavy_computation_with_pool, items)
        tasks.append(asyncio.create_task(rpc.run()))

    results = await asyncio.gather(*tasks)

    for i, result in enumerate(results):
        expected = [x * 2 for x in range(i * 10, (i + 1) * 10)]
        assert result == expected


async def test_queue_based_dynamic_computation(rpc_server):
    client_queue: asyncio.Queue[int | _QueueEndSentinel] = asyncio.Queue()
    rpc_queue = RpcQueue(client_queue)

    rpc = Rpc(rpc_server, queue_based_computation, rpc_queue)

    results = []

    async def collect_results():
        async for item in rpc.iterate():
            results.append(item)

    result_task = asyncio.create_task(collect_results())

    for i in range(20):
        await client_queue.put(i)
        await asyncio.sleep(0.01)

    await client_queue.put(_QUEUE_END)
    await result_task

    results.sort()
    expected = sorted([i * 3 for i in range(20)])
    assert results == expected


async def test_stress_concurrent_rpcs(rpc_server):
    num_rpcs = 20

    tasks = []
    for i in range(num_rpcs):
        items = list(range(5))
        rpc = Rpc(rpc_server, heavy_computation_with_pool, items)
        tasks.append(asyncio.create_task(rpc.run()))

    results = await asyncio.gather(*tasks)

    expected = [x * 2 for x in range(5)]
    for result in results:
        assert result == expected
