import asyncio
import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator, Awaitable, Callable, Generic, Optional, TypeVar

logger = logging.getLogger(f'uvicorn.{__name__}')

T = TypeVar('T')


class Stage(Generic[T]):
    def __init__(
        self,
        *,
        concurrency: int,
        process_func: Callable[[T], Awaitable[None]],
        name: str,
    ) -> None:
        self.name = name
        self._concurrency = concurrency
        self._process_func = process_func
        self._queue: asyncio.Queue[T | None] = asyncio.Queue()
        self._semaphore = asyncio.Semaphore(concurrency)
        self._next_queue: Stage[T] | None = None
        self._pipeline: Optional['_Pipeline[T]'] = None

    async def worker(self) -> None:
        while True:
            task = await self._queue.get()
            if task is None:
                self._queue.task_done()
                break

            try:
                async with self._semaphore:
                    logger.info(f"Processing task {task} in {self.name}")
                    await self._process_func(task)
                    if self._next_queue:
                        await self._next_queue._queue.put(task)
                    # Call the callback only if this is the last stage and pipeline has a callback
                    elif self._pipeline and self._pipeline.on_task_complete:
                        await self._pipeline.on_task_complete(task)
            except Exception as e:
                logger.error(f"Error processing task {task} in {self.name}: {e}")
                if self._pipeline and self._pipeline.on_task_error:
                    await self._pipeline.on_task_error(task, e)

            self._queue.task_done()
        logger.info(f"Worker in {self.name} stopped")

    def start_workers(self):
        asyncio.gather(*(self.worker() for _ in range(self._concurrency)))

    async def send_stop_signals(self) -> None:
        logger.info(f"Sending stop signals to {self.name}")
        for _ in range(self._concurrency):
            await self._queue.put(None)
        await self._queue.join()
        if self._next_queue:
            await self._next_queue.send_stop_signals()

    async def join(self) -> None:
        await self._queue.join()


class _Pipeline(Generic[T]):
    def __init__(self, queues: list[Stage[T]], on_task_complete: Callable[[T], Awaitable[None]] | None = None, on_task_error: Callable[[T, Exception], Awaitable[None]] | None = None) -> None:
        if len(queues) == 0:
            raise ValueError("Pipeline must have at least one queue")
        self.queues = queues
        self.on_task_complete = on_task_complete
        self.on_task_error = on_task_error

        # Set pipeline reference in all stages
        for queue in self.queues:
            queue._pipeline = self

        # Connect stages
        for current, next_queue in zip(self.queues, self.queues[1:]):
            current._next_queue = next_queue

        # Start all workers
        for queue in self.queues:
            queue.start_workers()

    async def push_task(self, task: T) -> None:
        logger.info(f"Pushing task {task}")
        await self.queues[0]._queue.put(task)

    async def stop(self) -> None:
        logger.info("Stopping pipeline")
        await self.queues[0].send_stop_signals()
        await asyncio.gather(*(queue.join() for queue in self.queues))


@asynccontextmanager
async def Pipeline(queues: list[Stage[T]], *, on_task_complete: Callable[[T], Awaitable[None]] | None = None, on_task_error: Callable[[T, Exception], Awaitable[None]] | None = None) -> AsyncIterator[_Pipeline[T]]:
    """Create and initialize a pipeline, yield it for use, then stop it when done.

    Args:
        queues: List of stage objects that form the pipeline
        on_task_complete: Optional callback function that is called when the last stage completes a task
        on_task_error: Optional callback function that is called when a stage encounters an error processing a task

    Usage:
        async with Pipeline(queues, on_task_complete=my_callback, on_task_error=my_error_handler) as pipeline:
            await pipeline.push_task(task)
    """
    pipeline = _Pipeline(queues, on_task_complete, on_task_error)

    try:
        yield pipeline
    finally:
        await pipeline.stop()
