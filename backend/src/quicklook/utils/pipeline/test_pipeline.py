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
            await handle.push(value)
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
        await handle.push(3)
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
            await handle.push(value)
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
            await handle.push(value)
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
            await handle.push(value)
        await asyncio.wait_for(done.wait(), timeout=1)

    assert sorted(results) == list(range(6))
    assert set(selection_order) == set(range(6))
    assert selection_order[2:] == sorted(selection_order[2:], reverse=True)


async def test_buffer_size_limit_blocks_when_full() -> None:
    """Test that _Buf blocks correctly when buffer is full."""
    from quicklook.utils.pipeline import _Buf
    
    # Test _Buf directly with size limit
    buf = _Buf(
        item_picker=lambda items: items.pop(0),
        max_size=2
    )
    
    # Fill buffer to capacity
    await buf.push(1)
    assert not buf.full(), "Buffer should not be full with 1 item (max 2)"
    
    await buf.push(2)
    assert buf.full(), "Buffer should be full with 2 items (max 2)"
    
    # Third push should block until something is consumed
    push_blocked = False
    
    async def attempt_push():
        nonlocal push_blocked
        push_blocked = True
        await buf.push(3)
        push_blocked = False
    
    push_task = asyncio.create_task(attempt_push())
    
    # Give time for push to start and block
    await asyncio.sleep(0.01)
    assert push_blocked, "Push should have started"
    assert not push_task.done(), "Push should be blocked on full buffer"
    
    # Consume an item to make space
    item = await buf.get()
    assert item == 1, "Should get first item"
    
    # Now push should complete
    await asyncio.wait_for(push_task, timeout=1)
    assert not push_blocked, "Push should have completed"
    assert buf.full(), "Buffer should be full again after push completed"


async def test_buffer_full_method() -> None:
    """Test that buffer full method works correctly."""
    async def process(item: int) -> int:
        await asyncio.sleep(0)
        return item

    pipeline = Pipeline(
        Stage[int, int](
            process=process,
            queue_capacity=1,  # Very small buffer
        )
    )

    async with pipeline.run() as handle:
        # Initially buffer should not be full
        assert not handle.full()
        
        # Add one item
        await handle.push(1)
        
        # Now buffer should be full
        assert handle.full()


async def test_pipeline_with_buffer_limits() -> None:
    """Integration test showing buffer limits work in a complete pipeline."""
    results: list[int] = []
    
    async def process(item: int) -> int:
        # Small delay to simulate work
        await asyncio.sleep(0.01)
        return item * 2
    
    async def on_finish(result: int) -> None:
        results.append(result)
    
    # Create pipeline with small buffer
    pipeline = Pipeline(
        Stage[int, int](
            process=process,
            queue_capacity=3,  # Small buffer
            parallel=2,
        )
    ).on_finish(on_finish)
    
    async with pipeline.run() as handle:
        # Push several items
        for i in range(5):
            await handle.push(i)
        
        # Wait a bit for processing
        await asyncio.sleep(0.1)
    
    # All items should be processed
    assert len(results) == 5
    assert set(results) == {0, 2, 4, 6, 8}  # Each input doubled
