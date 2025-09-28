import asyncio

import pytest

from . import FairSemaphore


async def test_async_with_limits_concurrency() -> None:
    sem = FairSemaphore()
    start = asyncio.Event()
    active = 0
    max_active = 0

    async def worker() -> None:
        nonlocal active, max_active
        await start.wait()
        async with sem:
            active += 1
            max_active = max(max_active, active)
            # タスクが同時に実行される機会を与える
            await asyncio.sleep(0)
            active -= 1

    tasks = [asyncio.create_task(worker()) for _ in range(3)]
    await asyncio.sleep(0)
    start.set()
    await asyncio.gather(*tasks)

    assert max_active == 1


async def test_async_with_releases_on_exception() -> None:
    sem = FairSemaphore()

    class Boom(Exception):
        pass

    with pytest.raises(Boom):
        async with sem:
            raise Boom()

    acquired = await asyncio.wait_for(sem.acquire(), timeout=0.1)
    assert acquired is True
    await sem.release()


async def test_async_with_returns_self() -> None:
    sem = FairSemaphore()

    async with sem as acquired:
        assert acquired is sem
