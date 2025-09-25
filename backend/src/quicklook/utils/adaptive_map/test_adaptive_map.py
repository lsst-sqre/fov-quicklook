"""Adaptive map モジュールの統合テスト"""

from __future__ import annotations

import asyncio
import contextlib
import time
from typing import Any, Awaitable, Callable, AsyncGenerator, cast
from unittest.mock import Mock

import pytest

from quicklook.utils.adaptive_map import (
    MapResult,
    Worker,
    WorkerDown,
    adaptive_map,
    create_worker,
    _AdaptiveMapRunner,
    _RunningTask,
)


class ControllableWorker(Worker):
    """テスト用に挙動を制御できるWorker実装"""

    def __init__(self, max_capacity: int = 1, name: str = "worker") -> None:
        self._name = name
        self._max_capacity = max_capacity
        self._current_capacity = max_capacity
        self._should_fail = False
        self._shutdown = False
        self._lock = asyncio.Lock()
        self._capacity_event = asyncio.Event()
        self._capacity_event.set()
        self.submitted_items: list[Any] = []
        self.per_item_delay: dict[Any, float] = {}

    def set_fail(self, should_fail: bool) -> None:
        self._should_fail = should_fail

    def set_delay(self, item: Any, delay: float) -> None:
        self.per_item_delay[item] = delay

    def capacity(self) -> int:
        if self._shutdown:
            return 0
        return self._current_capacity

    async def submit(self, func: Callable[..., Awaitable[Any]], *args, **kwargs) -> Any:
        async with self._lock:
            if self._shutdown:
                raise RuntimeError("Worker is shutdown")
            if self._should_fail:
                raise WorkerDown(f"Worker {self._name} failed")
            if self._current_capacity <= 0:
                raise RuntimeError("Worker has no capacity")

            self._current_capacity -= 1
            if self._current_capacity == 0:
                self._capacity_event.clear()

            item = args[0] if args else None
            if item is not None:
                self.submitted_items.append(item)
            delay = self.per_item_delay.get(item, 0.0)

        try:
            if delay:
                await asyncio.sleep(delay)
            return await func(*args, **kwargs)
        finally:
            async with self._lock:
                self._current_capacity += 1
                if self._current_capacity > 0:
                    self._capacity_event.set()

    async def wait_until_available(self) -> None:
        while not self._shutdown:
            if self._current_capacity > 0:
                return
            await self._capacity_event.wait()

    async def teardown(self) -> None:
        self._shutdown = True
        self._capacity_event.set()


async def short_task(value: int) -> int:
    await asyncio.sleep(0)
    return value * 2


async def slow_cancel_aware_task(item: int, cancel_log: list[int]) -> int:
    try:
        await asyncio.sleep(1.0)
        return item
    except asyncio.CancelledError:  # pragma: no cover - 例外経路をテストで確認
        cancel_log.append(item)
        raise


@pytest.mark.asyncio
async def test_create_worker_manages_capacity_and_teardown() -> None:
    calls: list[str] = []
    started = asyncio.Event()
    release = asyncio.Event()

    async def teardown() -> None:
        calls.append("teardown")

    async def submit(func: Callable[..., Awaitable[Any]], *args, **kwargs) -> Any:
        calls.append("submit")
        return await func(*args, **kwargs)

    worker = create_worker(teardown, 1, submit)

    async def long_task(value: int) -> int:
        started.set()
        await release.wait()
        return value * 2

    long_future = asyncio.create_task(worker.submit(long_task, 2))
    await started.wait()
    assert worker.capacity() == 0

    waiter = asyncio.create_task(worker.wait_until_available())
    await asyncio.sleep(0)
    assert not waiter.done()

    release.set()
    assert await long_future == 4
    await waiter
    assert worker.capacity() == 1

    async def increment(value: int) -> int:
        return value + 1

    assert await worker.submit(increment, 3) == 4

    await worker.teardown()
    assert "teardown" in calls


class TestAdaptiveMapRunner:
    async def test_initialization(self) -> None:
        worker = ControllableWorker()

        async def identity(item: int) -> int:
            return item

        items = [1, 2, 3]
        on_late = Mock()

        runner = _AdaptiveMapRunner(
            [worker],
            identity,
            items,
            on_late_result=on_late,
            cancel_on_reschedule=False,
            reschedule_threshold_multiplier=3.0,
        )

        assert runner.workers == [worker]
        assert runner.func is identity
        assert [(entry.index, entry.value) for entry in runner.remaining_items] == list(enumerate(items))
        assert runner.on_late_result is on_late
        assert runner.cancel_on_reschedule is False
        assert runner.reschedule_threshold_multiplier == 3.0
        assert runner.running_tasks == {}
        assert runner.completed_execution_times == []
        assert runner.yielded_item_indexes == set()
        assert runner.failed_workers == set()

    async def test_get_available_workers(self) -> None:
        ready = ControllableWorker(max_capacity=1, name="ready")
        busy = ControllableWorker(max_capacity=1, name="busy")
        busy._current_capacity = 0
        failing = ControllableWorker(max_capacity=1, name="failing")

        runner = _AdaptiveMapRunner([ready, busy, failing], short_task, [])
        runner.failed_workers.add(failing)

        available = runner._get_available_workers()
        assert available == [ready]

    async def test_select_best_worker(self) -> None:
        low = ControllableWorker(max_capacity=1, name="low")
        mid = ControllableWorker(max_capacity=1, name="mid")
        high = ControllableWorker(max_capacity=1, name="high")

        low._current_capacity = 1
        mid._current_capacity = 2
        high._current_capacity = 3

        runner = _AdaptiveMapRunner([low, mid, high], short_task, [])
        assert runner._select_best_worker([low, mid, high]) is high

    async def test_submit_new_tasks_basic(self) -> None:
        worker = ControllableWorker(max_capacity=2)
        runner = _AdaptiveMapRunner([worker], short_task, [1, 2, 3])

        await runner._submit_new_tasks()
        assert runner.running_tasks
        assert len(runner.remaining_items) < 3

        for task in list(runner.running_tasks):
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task

    async def test_submit_new_tasks_without_capacity(self) -> None:
        worker = ControllableWorker(max_capacity=0)
        runner = _AdaptiveMapRunner([worker], short_task, [1, 2])

        await runner._submit_new_tasks()
        assert runner.running_tasks == {}
        assert len(runner.remaining_items) == 2

    async def test_handle_completed_task_first_result(self) -> None:
        worker = ControllableWorker()

        async def double(value: int) -> int:
            return value * 2

        runner = _AdaptiveMapRunner([worker], double, [])
        task = asyncio.create_task(double(5))
        running = _RunningTask(worker=worker, item=5, item_index=0, task=task, start_time=time.time())
        runner.running_tasks[task] = running

        await task
        result = await runner._handle_completed_task(task)
        assert isinstance(result, MapResult)
        assert result.value == 10
        assert runner.yielded_item_indexes == {0}
        assert runner.completed_execution_times

    async def test_handle_completed_task_late_result(self) -> None:
        worker = ControllableWorker()
        on_late = Mock()

        async def double(value: int) -> int:
            return value * 2

        runner = _AdaptiveMapRunner([worker], double, [], on_late_result=on_late)
        runner.yielded_item_indexes.add(0)
        task = asyncio.create_task(double(5))
        running = _RunningTask(worker=worker, item=5, item_index=0, task=task, start_time=time.time())
        runner.running_tasks[task] = running

        await task
        result = await runner._handle_completed_task(task)
        assert result is None
        on_late.assert_called_once()
        assert runner.completed_execution_times == []

    async def test_handle_completed_task_worker_down(self) -> None:
        worker = ControllableWorker()

        async def failing(_: int) -> None:
            raise WorkerDown("boom")

        runner = _AdaptiveMapRunner([worker], failing, [])
        task = asyncio.create_task(failing(5))
        running = _RunningTask(worker=worker, item=5, item_index=0, task=task, start_time=time.time())
        runner.running_tasks[task] = running

        result = await runner._handle_completed_task(task)
        assert result is None
        assert worker in runner.failed_workers
        assert runner.remaining_items[0].value == 5

    async def test_handle_completed_task_other_exception(self) -> None:
        worker = ControllableWorker()

        async def failing(_: int) -> None:
            raise ValueError("error")

        runner = _AdaptiveMapRunner([worker], failing, [])
        task = asyncio.create_task(failing(5))
        running = _RunningTask(worker=worker, item=5, item_index=0, task=task, start_time=time.time())
        runner.running_tasks[task] = running

        with pytest.raises(ValueError, match="error"):
            await runner._handle_completed_task(task)

    async def test_calculate_reschedule_threshold_with_times(self) -> None:
        runner = _AdaptiveMapRunner([], short_task, [], reschedule_threshold_multiplier=2.5)
        runner.completed_execution_times = [1.0, 2.0, 3.0]
        assert runner._calculate_reschedule_threshold() == pytest.approx(2.0 * 2.5)

    async def test_calculate_reschedule_threshold_without_times(self) -> None:
        runner = _AdaptiveMapRunner([], short_task, [], reschedule_threshold_multiplier=2.5)
        assert runner._calculate_reschedule_threshold() == 0.0

    async def test_find_tasks_to_reschedule(self, monkeypatch: pytest.MonkeyPatch) -> None:
        worker = ControllableWorker()
        runner = _AdaptiveMapRunner([worker], short_task, [])

        long_task = asyncio.create_task(asyncio.sleep(0.05))
        short_task_future = asyncio.create_task(asyncio.sleep(0.05))

        long_running = _RunningTask(worker=worker, item=1, item_index=0, task=long_task, start_time=1.0)
        short_running = _RunningTask(worker=worker, item=2, item_index=1, task=short_task_future, start_time=4.0)
        runner.running_tasks = {long_task: long_running, short_task_future: short_running}

        monkeypatch.setattr(time, "time", lambda: 5.5)
        to_reschedule = runner._find_tasks_to_reschedule(2.0)
        assert to_reschedule == [(long_task, long_running)]

        for task in (long_task, short_task_future):
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task

    async def test_reschedule_task_moves_to_new_worker(self) -> None:
        old_worker = ControllableWorker(max_capacity=1, name="old")
        new_worker = ControllableWorker(max_capacity=2, name="new")

        async def identity(value: int) -> int:
            return value

        runner = _AdaptiveMapRunner([old_worker, new_worker], identity, [])
        original_task = asyncio.create_task(asyncio.sleep(0.1))
        running = _RunningTask(worker=old_worker, item=5, item_index=0, task=original_task, start_time=time.time())
        runner.running_tasks[original_task] = running

        await runner._reschedule_task(original_task, running)
        await asyncio.sleep(0)

        assert running.rescheduled is True
        assert original_task.cancelled()
        assert any(info.worker is new_worker for info in runner.running_tasks.values())

        for task in list(runner.running_tasks):
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task

    async def test_reschedule_task_without_available_workers(self) -> None:
        worker = ControllableWorker(max_capacity=0)
        runner = _AdaptiveMapRunner([worker], short_task, [])
        original_task = asyncio.create_task(asyncio.sleep(0.1))
        running = _RunningTask(worker=worker, item=5, item_index=0, task=original_task, start_time=time.time())
        runner.running_tasks[original_task] = running

        await runner._reschedule_task(original_task, running)
        assert runner.running_tasks == {original_task: running}
        assert running.rescheduled is False

        original_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await original_task

    async def test_reschedule_task_same_worker(self) -> None:
        worker = ControllableWorker(max_capacity=2)
        runner = _AdaptiveMapRunner([worker], short_task, [])
        original_task = asyncio.create_task(asyncio.sleep(0.1))
        running = _RunningTask(worker=worker, item=5, item_index=0, task=original_task, start_time=time.time())
        runner.running_tasks[original_task] = running

        await runner._reschedule_task(original_task, running)
        assert running.rescheduled is False
        assert len(runner.running_tasks) == 1

        original_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await original_task

    async def test_reschedule_task_without_cancellation(self) -> None:
        old_worker = ControllableWorker(max_capacity=1, name="old")
        new_worker = ControllableWorker(max_capacity=2, name="new")

        async def identity(value: int) -> int:
            return value

        runner = _AdaptiveMapRunner([old_worker, new_worker], identity, [], cancel_on_reschedule=False)
        original_task = asyncio.create_task(asyncio.sleep(0.1))
        running = _RunningTask(worker=old_worker, item=5, item_index=0, task=original_task, start_time=time.time())
        runner.running_tasks[original_task] = running

        await runner._reschedule_task(original_task, running)
        await asyncio.sleep(0)

        assert running.rescheduled is True
        assert not original_task.cancelled()

        for task in list(runner.running_tasks):
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task

    async def test_handle_rescheduling_skips_when_items_remaining(self) -> None:
        worker = ControllableWorker()
        runner = _AdaptiveMapRunner([worker], short_task, [1])

        pending_task = asyncio.create_task(asyncio.sleep(0.1))
        running = _RunningTask(worker=worker, item=1, item_index=0, task=pending_task, start_time=time.time())
        runner.running_tasks[pending_task] = running

        await runner._handle_rescheduling()
        assert running.rescheduled is False

        pending_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await pending_task

    async def test_handle_rescheduling_triggers_when_threshold_exceeded(self, monkeypatch: pytest.MonkeyPatch) -> None:
        slow = ControllableWorker(max_capacity=1, name="slow")
        fast = ControllableWorker(max_capacity=2, name="fast")

        async def identity(value: int) -> int:
            return value

        runner = _AdaptiveMapRunner(
            [slow, fast],
            identity,
            [],
            reschedule_threshold_multiplier=0.1,
        )
        runner.completed_execution_times = [1.0]
        runner.remaining_items.clear()

        pending_task = asyncio.create_task(asyncio.sleep(0.1))
        running = _RunningTask(worker=slow, item=1, item_index=0, task=pending_task, start_time=0.0)
        runner.running_tasks[pending_task] = running

        monkeypatch.setattr(time, "time", lambda: 5.0)
        await runner._handle_rescheduling()
        await asyncio.sleep(0)

        assert running.rescheduled is True
        assert any(info.worker is fast for info in runner.running_tasks.values() if info is not running)

        for task in list(runner.running_tasks):
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task

    async def test_run_empty_workers_and_items(self) -> None:
        runner = _AdaptiveMapRunner([], short_task, [])
        results = [result async for result in runner.run()]
        assert results == []

    async def test_run_without_workers_raises(self) -> None:
        runner = _AdaptiveMapRunner([], short_task, [1])
        with pytest.raises(ValueError, match="No available workers"):
            async for _ in runner.run():  # pragma: no cover - 例外で終了
                pass

    async def test_run_basic_execution(self) -> None:
        worker = ControllableWorker(max_capacity=2)
        runner = _AdaptiveMapRunner([worker], short_task, [1, 2, 3])

        results = [result async for result in runner.run()]
        assert sorted(result.value for result in results) == [2, 4, 6]

    async def test_run_cancels_pending_tasks_on_exit(self) -> None:
        worker = ControllableWorker(max_capacity=2)
        cancel_log: list[int] = []

        async def timed(item: int) -> int:
            if item == 1:
                await asyncio.sleep(0.01)
            else:
                await slow_cancel_aware_task(item, cancel_log)
            return item

        runner = _AdaptiveMapRunner([worker], timed, [1, 2])

        generator = runner.run()
        first_result = await generator.__anext__()
        assert first_result.item == 1

        await generator.aclose() # type: ignore
        await asyncio.sleep(0)

        assert cancel_log == [2]


class TestAdaptiveMapIntegration:
    async def test_requires_workers(self) -> None:
        async def identity(item: int) -> int:
            return item

        with pytest.raises(ValueError, match="No available workers"):
            async for _ in adaptive_map([], identity, [1, 2]):  # pragma: no cover - 例外で終了
                pass

    async def test_handles_empty_items(self) -> None:
        worker = ControllableWorker()
        results = [result async for result in adaptive_map([worker], short_task, [])]
        assert results == []

    async def test_single_worker_single_item(self) -> None:
        worker = ControllableWorker()
        results = [result async for result in adaptive_map([worker], short_task, [3])]
        assert len(results) == 1
        assert results[0].item == 3
        assert results[0].value == 6
        assert isinstance(results[0], MapResult)

    async def test_worker_failure_reassigns_work(self) -> None:
        failing = ControllableWorker(max_capacity=1, name="failing")
        stable = ControllableWorker(max_capacity=1, name="stable")
        failing.set_fail(True)

        async def identity(item: int) -> int:
            return item

        results = [result async for result in adaptive_map([failing, stable], identity, [1, 2, 3])]
        result_values = [res.value for res in results]
        assert sorted(result_values) == [1, 2, 3]
        assert all(res.worker is stable for res in results)

    async def test_exception_propagation(self) -> None:
        worker = ControllableWorker()

        async def failing(item: int) -> int:
            if item == 2:
                raise ValueError("boom")
            return item

        with pytest.raises(ValueError, match="boom"):
            async for _ in adaptive_map([worker], failing, [1, 2, 3]):
                pass

    async def test_late_result_callback_invoked(self) -> None:
        fast = ControllableWorker(max_capacity=1, name="fast")
        slow = ControllableWorker(max_capacity=1, name="slow")
        slow.set_delay(2, 0.2)

        late_results: list[MapResult] = []

        def on_late(result: MapResult) -> None:
            late_results.append(result)

        async def identity(item: int) -> int:
            await asyncio.sleep(0)
            return item

        results = [
            result
            async for result in adaptive_map(
                [fast, slow],
                identity,
                [1, 2],
                on_late_result=on_late,
                cancel_on_reschedule=False,
                reschedule_threshold_multiplier=0.05,
            )
        ]

        await asyncio.sleep(0.1)

        assert {res.item for res in results} == {1, 2}
        assert late_results
        assert all(res.item == 2 for res in late_results)
