from __future__ import annotations

import asyncio
import time
from collections.abc import Awaitable, Callable
from contextlib import suppress
from typing import Any
import uuid

import pytest

from . import MapResult, Worker, WorkerDown, adaptive_map, create_worker


pytestmark = pytest.mark.asyncio


class ControllableWorker(Worker):
    """テスト向けに挙動を制御できるWorker実装"""

    def __init__(
        self,
        *,
        max_capacity: int = 1,
        name: str = "worker",
        process: Callable[[Any], Awaitable[Any]] | None = None,
    ) -> None:
        self._name = name
        self._capacity = max_capacity
        self._lock = asyncio.Lock()
        self._available = asyncio.Event()
        self._available.set()
        self._shutdown = False
        self.submitted: list[Any] = []
        self._delays: dict[Any, float] = {}
        self._fail_items: set[Any] = set()

        if process is None:

            async def _identity(item: Any) -> Any:
                await asyncio.sleep(0)
                return item

            self._process: Callable[[Any], Awaitable[Any]] = _identity
        else:
            self._process = process

    def id(self):
        return self._name

    def capacity(self) -> int:
        if self._shutdown:
            return 0
        return self._capacity

    async def submit(self, item: Any) -> Any:
        async with self._lock:
            if self._shutdown:
                raise RuntimeError("Worker is shutdown")
            if self._capacity <= 0:
                raise RuntimeError("Worker has no capacity")
            self._capacity -= 1
            if self._capacity == 0:
                self._available.clear()

        try:
            self.submitted.append(item)
            if item in self._fail_items:
                self._fail_items.remove(item)
                raise WorkerDown(f"Worker {self._name} failed for item {item}")

            delay = self._delays.get(item, 0.0)
            if delay:
                await asyncio.sleep(delay)
            return await self._process(item)
        finally:
            async with self._lock:
                self._capacity += 1
                if self._capacity > 0:
                    self._available.set()

    async def wait_until_available(self) -> None:
        while not self._shutdown:
            if self._capacity > 0:
                return
            await self._available.wait()

    async def teardown(self) -> None:
        self._shutdown = True
        self._available.set()

    def set_delay(self, item: Any, delay: float) -> None:
        self._delays[item] = delay

    def set_process(self, process: Callable[[Any], Awaitable[Any]]) -> None:
        self._process = process

    def fail_for(self, item: Any) -> None:
        self._fail_items.add(item)


async def test_create_worker_manages_capacity_and_teardown() -> None:
    calls: list[str] = []
    started = asyncio.Event()
    release = asyncio.Event()

    async def teardown() -> None:
        calls.append("teardown")

    async def process_item(coro: Awaitable[int]) -> int:
        calls.append("process")
        return await coro

    worker = create_worker(str(uuid.uuid4()), process_item, max_concurrency=1, teardown=teardown)

    async def long_task() -> int:
        started.set()
        await release.wait()
        return 42

    running = asyncio.create_task(worker.submit(long_task()))
    await started.wait()
    assert worker.capacity() == 0

    waiter = asyncio.create_task(worker.wait_until_available())
    await asyncio.sleep(0)
    assert not waiter.done()

    release.set()
    assert await running == 42
    await waiter
    assert worker.capacity() == 1

    value = await worker.submit(asyncio.sleep(0, result=7))
    assert value == 7

    await worker.teardown()
    assert "teardown" in calls


async def test_adaptive_map_basic_flow() -> None:
    async def process_item(item: int) -> int:
        await asyncio.sleep(0)
        return item * 2

    worker = create_worker(str(uuid.uuid4()), process_item, max_concurrency=2)
    items = [1, 2, 3]

    results = [result async for result in adaptive_map([worker], items)]

    assert sorted(result.item for result in results) == items
    assert sorted(result.value for result in results) == [2, 4, 6]
    assert all(result.worker is worker for result in results)

    await worker.teardown()


async def test_adaptive_map_worker_failure_reschedules() -> None:
    async def process(item: int) -> int:
        await asyncio.sleep(0)
        return item

    fast = ControllableWorker(max_capacity=1, name="fast", process=process)
    slow = ControllableWorker(max_capacity=1, name="slow", process=process)

    slow.set_delay(2, 0.05)
    slow.set_delay(3, 0.01)
    fast.fail_for(2)

    results = [result async for result in adaptive_map([fast, slow], [1, 2, 3])]
    worker_by_item = {result.item: result.worker for result in results}

    assert worker_by_item[2] is slow
    assert set(worker_by_item) == {1, 2, 3}

    await fast.teardown()
    await slow.teardown()


async def test_adaptive_map_late_results_callback_called() -> None:
    fast = ControllableWorker(max_capacity=1, name="fast")
    slow = ControllableWorker(max_capacity=1, name="slow")

    async def fast_process(item: int) -> int:
        await asyncio.sleep(0.01)
        return item

    async def slow_process(item: int) -> int:
        delay = 0.3 if item == 2 else 0.05
        await asyncio.sleep(delay)
        return item

    fast.set_process(fast_process)
    slow.set_process(slow_process)

    late_results: list[MapResult] = []

    results = [
        result
        async for result in adaptive_map(
            [fast, slow],
            [1, 2],
            on_late_result=late_results.append,
            cancel_on_reschedule=False,
            reschedule_threshold_multiplier=0.05,
        )
    ]

    assert {result.item for result in results} == {1, 2}
    assert any(res.item == 2 and res.worker is slow for res in late_results)

    await fast.teardown()
    await slow.teardown()


async def test_readme_example_runs() -> None:
    async def process_item(item: tuple[Callable[..., Awaitable[Any]], Any]) -> Any:
        func, *args = item
        return await func(*args)

    worker = create_worker(str(uuid.uuid4()), process_item, max_concurrency=3)

    async def square(x: int) -> int:
        await asyncio.sleep(0)
        return x * x

    items = [(square, i) for i in range(5)]
    results: list[int] = []

    async for result in adaptive_map([worker], items):
        results.append(result.value)

    await worker.teardown()

    assert sorted(results) == [0, 1, 4, 9, 16]


@pytest.mark.parametrize(
    "num_items,max_concurrency,worker_count,expected_duration",
    [
        (2, 1, 1, 0.2),
        (2, 2, 1, 0.1),
        (2, 1, 2, 0.1),
        (3, 1, 3, 0.1),
        (4, 1, 2, 0.2),
        (4, 2, 1, 0.2),
        (6, 2, 2, 0.2),
    ],
)
async def test_adaptive_map_throughput_patterns(num_items: int, max_concurrency: int, worker_count: int, expected_duration: float) -> None:
    async def process_item(item: int) -> int:
        await asyncio.sleep(0.1)
        return item

    workers = [create_worker(str(uuid.uuid4()), process_item, max_concurrency=max_concurrency) for _ in range(worker_count)]
    items = list(range(num_items))

    start = time.perf_counter()
    results = [result async for result in adaptive_map(workers, items)]
    elapsed = time.perf_counter() - start

    assert sorted(result.item for result in results) == items
    assert elapsed == pytest.approx(expected_duration, rel=0.3, abs=0.05)

    await asyncio.gather(*(worker.teardown() for worker in workers))


async def _run_reschedule_case(multiplier: float) -> tuple[list[MapResult], float, list[MapResult], ControllableWorker, ControllableWorker]:
    items = [0, 1, 2, 3]

    fast = ControllableWorker(max_capacity=2, name="fast")
    slow = ControllableWorker(max_capacity=1, name="slow")

    for item in items:
        fast.set_delay(item, 0.1)
        slow.set_delay(item, 0.35)

    late_results: list[MapResult] = []
    generator = adaptive_map(
        [fast, slow],
        items,
        on_late_result=late_results.append,
        cancel_on_reschedule=False,
        reschedule_threshold_multiplier=multiplier,
    )

    start = time.perf_counter()
    results: list[MapResult] = []
    first_elapsed: float | None = None
    async for result in generator:
        results.append(result)
        if len(results) == len(items) and first_elapsed is None:
            first_elapsed = time.perf_counter() - start

    assert len(results) == len(items)

    if first_elapsed is None:
        pytest.fail("adaptive_map did not yield completion timings")

    await fast.teardown()
    await slow.teardown()

    return results, first_elapsed, late_results, fast, slow


async def test_adaptive_map_reschedule_pattern_improves_latency() -> None:
    baseline_results, baseline_elapsed, baseline_late, baseline_fast, baseline_slow = await _run_reschedule_case(10.0)
    dynamic_results, dynamic_elapsed, dynamic_late, dynamic_fast, dynamic_slow = await _run_reschedule_case(1.1)

    assert len(baseline_results) == len(dynamic_results) == 4
    assert not baseline_late
    assert dynamic_late
    assert dynamic_elapsed < baseline_elapsed - 0.03

    item_to_worker = {result.item: result.worker for result in dynamic_results}
    shared_items = set(dynamic_fast.submitted).intersection(dynamic_slow.submitted)
    assert shared_items
    assert any(item_to_worker[item] is dynamic_fast for item in shared_items)


async def test_create_worker_rejects_nonpositive_concurrency() -> None:
    async def process_item(value: int) -> int:
        return value

    with pytest.raises(ValueError):
        create_worker(str(uuid.uuid4()), process_item, max_concurrency=0)


async def test_adaptive_map_requires_workers_when_items() -> None:
    gen = adaptive_map([], [1])
    with pytest.raises(ValueError):
        await gen.__anext__()


async def test_adaptive_map_handles_empty_workers_and_items() -> None:
    results = [result async for result in adaptive_map([], [])]
    assert results == []


async def test_helper_worker_submit_waits_for_capacity() -> None:
    started: list[str] = []
    first_done = asyncio.Event()
    second_done = asyncio.Event()

    async def process_item(item: str) -> str:
        started.append(item)
        if item == "first":
            await first_done.wait()
        else:
            await second_done.wait()
        return item

    worker = create_worker(str(uuid.uuid4()), process_item, max_concurrency=1)

    tasks = [
        asyncio.create_task(worker.submit("first")),
        asyncio.create_task(worker.submit("second")),
    ]

    try:
        await asyncio.sleep(0)
        assert started == ["first"]

        first_done.set()
        assert await asyncio.wait_for(tasks[0], timeout=1.0) == "first"

        await asyncio.sleep(0)
        assert started == ["first", "second"]

        second_done.set()
        assert await asyncio.wait_for(tasks[1], timeout=1.0) == "second"
    finally:
        for task in tasks:
            if not task.done():
                task.cancel()
        for task in tasks:
            with suppress(asyncio.CancelledError):
                await task

    await worker.teardown()


async def test_helper_worker_capacity_zero_after_teardown() -> None:
    async def process_item(item: int) -> int:
        return item

    worker = create_worker(str(uuid.uuid4()), process_item, max_concurrency=1)
    await worker.teardown()
    assert worker.capacity() == 0
