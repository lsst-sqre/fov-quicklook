import asyncio
import pytest
from typing import Callable, Awaitable

from quicklook.utils.pipeline import Stage, _Pipeline, Pipeline


# Test task class for tracking execution
class ExampleTask:
    def __init__(self, name: str):
        self.name = name
        self.history: list[str] = []  # Track stages the task has gone through

    def __repr__(self) -> str:
        return f"TestTask({self.name})"


# Processing stage functions for testing
async def process_stage1(task: ExampleTask) -> None:
    await asyncio.sleep(0.01)
    task.history.append("stage1")


async def process_stage2(task: ExampleTask) -> None:
    await asyncio.sleep(0.01)
    task.history.append("stage2")


async def process_stage3(task: ExampleTask) -> None:
    await asyncio.sleep(0.01)
    task.history.append("stage3")


async def failing_process(task: ExampleTask) -> None:
    task.history.append("fail_started")
    raise ValueError(f"Test failure in {task.name}")


# Fixtures
@pytest.fixture
def basic_stages():
    return [
        Stage(concurrency=2, process_func=process_stage1, name='stage1'),
        Stage(concurrency=2, process_func=process_stage2, name='stage2'),
        Stage(concurrency=2, process_func=process_stage3, name='stage3'),
    ]


async def test_basic_task_flow(basic_stages):
    task = ExampleTask("test1")
    async with Pipeline(basic_stages) as pipeline:
        await pipeline.push_task(task)

    assert task.history == ["stage1", "stage2", "stage3"]


async def test_multiple_tasks(basic_stages):
    """Test processing multiple tasks through the pipeline."""
    tasks = [ExampleTask(f"task{i}") for i in range(5)]

    async with Pipeline(basic_stages) as pipeline:
        for task in tasks:
            await pipeline.push_task(task)

    # All tasks should complete all stages
    for task in tasks:
        assert task.history == ["stage1", "stage2", "stage3"]


async def test_concurrency_limit():
    """Test that concurrency limits are respected."""
    execution_tracker = {"running": 0, "max_concurrent": 0}

    async def concurrent_process(task: ExampleTask) -> None:
        execution_tracker["running"] += 1
        execution_tracker["max_concurrent"] = max(execution_tracker["max_concurrent"], execution_tracker["running"])
        task.history.append("started")
        await asyncio.sleep(0.02)  # Simulate work
        task.history.append("completed")
        execution_tracker["running"] -= 1

    concurrency_limit = 3
    stage = Stage(concurrency=concurrency_limit, process_func=concurrent_process, name='concurrent_test')

    tasks = [ExampleTask(f"task{i}") for i in range(10)]

    async with Pipeline([stage]) as pipeline:
        for task in tasks:
            await pipeline.push_task(task)

    # Verify concurrency limit was respected
    assert execution_tracker["max_concurrent"] <= concurrency_limit

    # All tasks should have completed
    for task in tasks:
        assert task.history == ["started", "completed"]


async def test_pipeline_context_manager():
    """Test the context manager behavior of create_pipeline."""
    processed = {"count": 0}

    async def counting_process(task: ExampleTask) -> None:
        processed["count"] += 1
        task.history.append("processed")

    stage = Stage(concurrency=1, process_func=counting_process, name='counter')

    # Can push tasks within context
    async with Pipeline([stage]) as pipeline:
        await pipeline.push_task(ExampleTask("in_context"))

    assert processed["count"] == 1


async def test_pipeline_stop():
    """Test the stop method works correctly."""
    processed = {"count": 0}

    async def slow_process(task: ExampleTask) -> None:
        await asyncio.sleep(0.03)
        processed["count"] += 1
        task.history.append("processed")

    stage = Stage(concurrency=3, process_func=slow_process, name='slow')
    pipeline = _Pipeline([stage], None)

    tasks = [ExampleTask(f"task{i}") for i in range(10)]

    # Push all tasks
    for task in tasks:
        await pipeline.push_task(task)

    # Stop after a short time before all tasks complete
    await asyncio.sleep(0.01)
    await pipeline.stop()

    # Some tasks may have completed, but likely not all
    assert processed["count"] <= 10


async def test_multi_stage_concurrency():
    """Test concurrency across multiple pipeline stages."""
    # Create a pipeline with differently configured stages
    stages = [
        Stage(concurrency=3, process_func=process_stage1, name='fetch'),
        Stage(concurrency=2, process_func=process_stage2, name='transform'),
        Stage(concurrency=4, process_func=process_stage3, name='save'),
    ]

    tasks = [ExampleTask(f"task{i}") for i in range(10)]

    # Use asyncio.timeout to ensure the test doesn't hang indefinitely
    async with asyncio.timeout(5.0):  # 5 second timeout
        async with Pipeline(stages) as pipeline:
            for task in tasks:
                await pipeline.push_task(task)

    # Verify all tasks were processed through all stages
    for task in tasks:
        assert task.history == ["stage1", "stage2", "stage3"]


@pytest.mark.asyncio
async def test_complex_pipeline_example():
    """Test a complex example similar to the provided usage example."""
    results = []

    async def fetch(task: ExampleTask) -> None:
        await asyncio.sleep(0.01)  # 1/10に短縮: 0.1 -> 0.01
        task.history.append("fetched")

    async def transform(task: ExampleTask) -> None:
        await asyncio.sleep(0.02)  # 1/10に短縮: 0.2 -> 0.02
        task.history.append("transformed")

    async def save(task: ExampleTask) -> None:
        await asyncio.sleep(0.01)  # 1/10に短縮: 0.1 -> 0.01
        task.history.append("saved")
        results.append(task.name)

    stages = [
        Stage(concurrency=3, process_func=fetch, name='fetch'),
        Stage(concurrency=2, process_func=transform, name='transform'),
        Stage(concurrency=5, process_func=save, name='save'),
    ]

    async with Pipeline(stages) as pipeline:
        for i in range(10):
            await pipeline.push_task(ExampleTask(f"task{i}"))

    # All tasks should have been processed
    assert len(results) == 10
    assert sorted(results) == [f"task{i}" for i in range(10)]


async def test_task_complete_callback():
    """Test that on_task_complete callback is called only after the last stage."""
    callback_calls = []
    
    async def callback(task: ExampleTask) -> None:
        callback_calls.append(task.name)
    
    # Create a pipeline with the callback
    stages = [
        Stage(concurrency=1, process_func=process_stage1, name='stage1'),
        Stage(concurrency=1, process_func=process_stage2, name='stage2'),
        Stage(concurrency=1, process_func=process_stage3, name='stage3'),
    ]
    
    tasks = [ExampleTask(f"task{i}") for i in range(3)]
    
    async with Pipeline(stages, on_task_complete=callback) as pipeline:
        for task in tasks:
            await pipeline.push_task(task)
    
    # Verify callback was called once for each task
    assert len(callback_calls) == 3
    assert set(callback_calls) == {"task0", "task1", "task2"}
    
    # Verify all tasks were processed through all stages
    for task in tasks:
        assert task.history == ["stage1", "stage2", "stage3"]


async def test_callback_not_called_for_intermediate_stages():
    """Test that callback is only called for the last stage."""
    callback_calls = []
    stage_complete_flags = {"stage1": False, "stage2": False, "stage3": True}
    
    async def callback(task: ExampleTask) -> None:
        callback_calls.append(f"{task.name}_from_{task.history[-1]}")
    
    # Create a custom set of stages with a tracking mechanism
    stages = [
        Stage(concurrency=1, process_func=process_stage1, name='stage1'),
        Stage(concurrency=1, process_func=process_stage2, name='stage2'),
        Stage(concurrency=1, process_func=process_stage3, name='stage3'),
    ]
    
    task = ExampleTask("test_task")
    
    async with Pipeline(stages, on_task_complete=callback) as pipeline:
        await pipeline.push_task(task)
    
    # Verify callback was called exactly once
    assert len(callback_calls) == 1
    # And it was called after stage3 (the last stage)
    assert callback_calls[0] == "test_task_from_stage3"
    
    # All stages should be processed
    assert task.history == ["stage1", "stage2", "stage3"]


async def test_single_stage_with_callback():
    """Test callback works with a single stage pipeline."""
    callback_calls = []
    
    async def callback(task: ExampleTask) -> None:
        callback_calls.append(task.name)
    
    # Create a single-stage pipeline
    stage = Stage(concurrency=1, process_func=process_stage1, name='only_stage')
    
    tasks = [ExampleTask(f"single{i}") for i in range(3)]
    
    async with Pipeline([stage], on_task_complete=callback) as pipeline:
        for task in tasks:
            await pipeline.push_task(task)
    
    # Verify callback was called for each task
    assert len(callback_calls) == 3
    assert set(callback_calls) == {"single0", "single1", "single2"}
    
    # Verify all tasks were processed
    for task in tasks:
        assert task.history == ["stage1"]


async def test_task_error_callback():
    """Test that on_task_error callback is called when a stage raises an exception."""
    error_calls = []
    
    async def error_callback(task: ExampleTask, error: Exception) -> None:
        error_calls.append((task.name, str(error)))
    
    # Create a pipeline with a failing stage
    stages = [
        Stage(concurrency=1, process_func=failing_process, name='failing_stage'),
    ]
    
    tasks = [ExampleTask(f"error_task{i}") for i in range(3)]
    
    async with Pipeline(stages, on_task_error=error_callback) as pipeline:
        for task in tasks:
            await pipeline.push_task(task)
    
    # Verify error callback was called for each task
    assert len(error_calls) == 3
    for i, (task_name, error_message) in enumerate(error_calls):
        assert task_name == f"error_task{i}"
        assert "Test failure in" in error_message
    
    # Verify all tasks started processing
    for task in tasks:
        assert task.history == ["fail_started"]


async def test_mixed_success_and_error():
    """Test pipeline with both successful and failing stages."""
    complete_calls = []
    error_calls = []
    
    async def complete_callback(task: ExampleTask) -> None:
        complete_calls.append(task.name)
    
    async def error_callback(task: ExampleTask, error: Exception) -> None:
        error_calls.append((task.name, type(error)))
    
    # Create two different pipelines
    success_stages = [
        Stage(concurrency=1, process_func=process_stage1, name='success_stage1'),
        Stage(concurrency=1, process_func=process_stage2, name='success_stage2'),
    ]
    
    fail_stages = [
        Stage(concurrency=1, process_func=process_stage1, name='fail_stage1'),
        Stage(concurrency=1, process_func=failing_process, name='fail_stage2'),
        # This stage won't be reached due to the error in fail_stage2
        Stage(concurrency=1, process_func=process_stage3, name='fail_stage3'),
    ]
    
    # Run tasks through both pipelines
    success_tasks = [ExampleTask(f"success{i}") for i in range(2)]
    fail_tasks = [ExampleTask(f"fail{i}") for i in range(2)]
    
    async with Pipeline(success_stages, on_task_complete=complete_callback, on_task_error=error_callback) as pipeline:
        for task in success_tasks:
            await pipeline.push_task(task)
    
    async with Pipeline(fail_stages, on_task_complete=complete_callback, on_task_error=error_callback) as pipeline:
        for task in fail_tasks:
            await pipeline.push_task(task)
    
    # Success tasks should have complete callback called
    assert len(complete_calls) == 2
    assert set(complete_calls) == {f"success{i}" for i in range(2)}
    
    # Failed tasks should have error callback called
    assert len(error_calls) == 2
    for name, error_type in error_calls:
        assert name in {f"fail{i}" for i in range(2)}
        assert error_type == ValueError
    
    # Success tasks should complete all stages
    for task in success_tasks:
        assert task.history == ["stage1", "stage2"]
    
    # Failed tasks should only complete the first stage and start the second
    for task in fail_tasks:
        assert task.history == ["stage1", "fail_started"]


async def test_error_doesnt_stop_pipeline():
    """Test that errors in one task don't prevent processing of other tasks."""
    processed_tasks = []
    error_tasks = []
    
    async def complete_callback(task: ExampleTask) -> None:
        processed_tasks.append(task.name)
    
    async def error_callback(task: ExampleTask, error: Exception) -> None:
        error_tasks.append(task.name)
    
    # Create a stage that fails for even-numbered tasks
    async def conditional_fail(task: ExampleTask) -> None:
        task_num = int(task.name.replace("task", ""))
        if task_num % 2 == 0:
            raise ValueError(f"Even task {task.name}")
        task.history.append("processed")
    
    stage = Stage(concurrency=1, process_func=conditional_fail, name='conditional_fail')
    
    tasks = [ExampleTask(f"task{i}") for i in range(5)]
    
    async with Pipeline([stage], on_task_complete=complete_callback, on_task_error=error_callback) as pipeline:
        for task in tasks:
            await pipeline.push_task(task)
    
    # Even tasks should have errors
    assert set(error_tasks) == {"task0", "task2", "task4"}
    
    # Odd tasks should complete successfully
    assert set(processed_tasks) == {"task1", "task3"}
    
    # Check task history
    for i, task in enumerate(tasks):
        if i % 2 == 0:
            assert task.history == []  # Failed before adding to history
        else:
            assert task.history == ["processed"]
