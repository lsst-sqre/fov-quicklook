import pytest
import asyncio
from src.quicklook.utils.broadcastqueue import BroadcastQueue


async def test_broadcast_queue_subscription():
    queue = BroadcastQueue[int]()
    ready = asyncio.Event()

    async def subscriber(queue: BroadcastQueue[int], results: list):
        with queue.subscribe() as sub:
            ready.set()
            results.append(await sub.get())

    results = []
    async with asyncio.TaskGroup() as tg:
        tg.create_task(subscriber(queue, results))
        await ready.wait()
        queue.put(42)

    assert results == [42]


async def test_broadcast_queue_multiple_subscriptions():
    queue = BroadcastQueue[int]()

    results1 = []
    results2 = []

    ready = asyncio.Queue()

    async def subscriber(queue: BroadcastQueue[int], results: list):
        with queue.subscribe() as sub:
            ready.put_nowait(None)
            results.append(await sub._q.get())

    async with asyncio.TaskGroup() as tg:
        tg.create_task(subscriber(queue, results1))
        tg.create_task(subscriber(queue, results2))

        for _ in range(2):
            await ready.get()

        queue.put(99)

    assert results1 == [99]
    assert results2 == [99]
