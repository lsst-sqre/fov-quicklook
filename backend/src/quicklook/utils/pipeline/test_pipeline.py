import asyncio

import pytest

from quicklook.utils.pipeline import Pipeline, Skip, Stage


@pytest.fixture
def pipeline_fixture() -> Pipeline[int, str]:
    async def int2str(item: int) -> str:
        return {
            0: 'zero',
            1: 'one',
            2: 'two',
        }[item]

    async def str2upper(item: str) -> str:
        return item.upper()

    return Pipeline(
        Stage[int, str](
            process=int2str,
        )
    ).append(
        Stage[str, str](
            process=str2upper,
        )
    )


async def test_pipeline_processes_items(pipeline_fixture: Pipeline[int, str]) -> None:
    results: list[str] = []
    done = asyncio.Event()

    async def on_finish(item: str) -> None:
        results.append(item)
        if len(results) == 3:
            done.set()

    async with pipeline_fixture.on_finish(on_finish).run() as handle:
        for value in (0, 1, 2):
            handle.push(value)
        await asyncio.wait_for(done.wait(), timeout=1)

    assert results == ['ZERO', 'ONE', 'TWO']


async def test_pipeline_invokes_stage_hooks() -> None:
    on_enter_calls: list[int] = []
    on_exit_calls: list[tuple[int, int]] = []
    finished = asyncio.Event()
    results: list[int] = []

    async def on_enter(item: int) -> None:
        on_enter_calls.append(item)

    async def process(item: int) -> int:
        await asyncio.sleep(0)
        return item * 2

    async def on_exit(item: int, result: int) -> None:
        on_exit_calls.append((item, result))

    async def on_finish(result: int) -> None:
        results.append(result)
        finished.set()

    pipeline = Pipeline(
        Stage[int, int](
            process=process,
            on_enter=on_enter,
            on_exit=on_exit,
        )
    ).on_finish(on_finish)

    async with pipeline.run() as handle:
        handle.push(3)
        await asyncio.wait_for(finished.wait(), timeout=1)

    assert results == [6]
    assert on_enter_calls == [3]
    assert on_exit_calls == [(3, 6)]


async def test_pipeline_skips_items() -> None:
    results: list[int] = []
    on_exit_calls: list[tuple[int, int]] = []
    done = asyncio.Event()

    async def process(item: int) -> int:
        if item % 2 == 0:
            raise Skip()
        await asyncio.sleep(0)
        return item

    async def on_exit(item: int, result: int) -> None:
        on_exit_calls.append((item, result))

    async def on_finish(result: int) -> None:
        results.append(result)
        if len(results) == 2:
            done.set()

    pipeline = Pipeline(
        Stage[int, int](
            process=process,
            on_exit=on_exit,
        )
    ).on_finish(on_finish)

    async with pipeline.run() as handle:
        for value in (0, 1, 2, 3):
            handle.push(value)
        await asyncio.wait_for(done.wait(), timeout=1)

    assert results == [1, 3]
    assert on_exit_calls == [(1, 1), (3, 3)]


async def test_pipeline_respects_parallel_limit() -> None:
    lock = asyncio.Lock()
    active_workers = 0
    max_active_workers = 0
    results: list[int] = []
    done = asyncio.Event()

    async def process(item: int) -> int:
        nonlocal active_workers, max_active_workers
        async with lock:
            active_workers += 1
            max_active_workers = max(max_active_workers, active_workers)
        try:
            await asyncio.sleep(0.01)
            return item
        finally:
            async with lock:
                active_workers -= 1

    async def on_finish(result: int) -> None:
        results.append(result)
        if len(results) == 6:
            done.set()

    pipeline = Pipeline(
        Stage[int, int](
            process=process,
            parallel=2,
        )
    ).on_finish(on_finish)

    async with pipeline.run() as handle:
        for value in range(6):
            handle.push(value)
        await asyncio.wait_for(done.wait(), timeout=1)

    assert max_active_workers == 2
    assert sorted(results) == list(range(6))


async def test_pipeline_custom_item_picker_prioritizes_latest() -> None:
    selection_order: list[int] = []
    selection_lock = asyncio.Lock()
    results: list[int] = []
    done = asyncio.Event()

    async def stage1(item: int) -> int:
        await asyncio.sleep(0)
        return item

    async def stage2_process(item: int) -> int:
        await asyncio.sleep(0.005)
        return item

    async def stage2_on_enter(item: int) -> None:
        async with selection_lock:
            selection_order.append(item)

    def pick_highest(items: list[int]) -> int:
        max_index = max(range(len(items)), key=items.__getitem__)
        return items.pop(max_index)

    async def on_finish(result: int) -> None:
        results.append(result)
        if len(results) == 6:
            done.set()

    pipeline = Pipeline(
        Stage[int, int](
            process=stage1,
        )
    ).append(
        Stage[int, int](
            process=stage2_process,
            item_picker=pick_highest,
            on_enter=stage2_on_enter,
            parallel=2,
        )
    ).on_finish(on_finish)

    async with pipeline.run() as handle:
        for value in range(6):
            handle.push(value)
        await asyncio.wait_for(done.wait(), timeout=1)

    assert sorted(results) == list(range(6))
    assert set(selection_order) == set(range(6))
    assert selection_order[2:] == sorted(selection_order[2:], reverse=True)
