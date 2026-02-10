from __future__ import annotations

import asyncio
import contextlib
import inspect
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Generic, ParamSpec, TypeVar

import quicklook.mylogging

logger = quicklook.mylogging.getLogger(__name__)


P = ParamSpec('P')
I = TypeVar('I')
I2 = TypeVar('I2')
R = TypeVar('R')
R2 = TypeVar('R2')


async def _noop_async(*args):
    pass


class Pipeline(Generic[I, R]):
    _stage_defs: list[Stage]
    _on_finish: Callable[..., Awaitable[None]] = _noop_async

    def __init__(self, first_stage: Stage[I, R]):
        self._stage_defs = [first_stage]

    def append(self, another_stage: Stage[R, R2]) -> Pipeline[I, R2]:
        self._stage_defs.append(another_stage)
        return self  # type: ignore

    def on_finish(self, callback: Callable[[R], Awaitable[None]]) -> Pipeline[I, R]:
        self._on_finish = callback
        return self

    # def concat(self, another_pipeline: Pipeline[R, R2]) -> Pipeline[I, R2]:
    #     self._stage_defs.extend(another_pipeline._stage_defs)
    #     return self  # type: ignore

    @contextlib.asynccontextmanager
    async def run(self):
        async with _run_pipeline(self) as pipeline_handle:
            yield pipeline_handle


@dataclass
class Stage(Generic[I, R]):
    process: Callable[[I], Awaitable[R]]
    parallel: int = 1
    item_picker: Callable[[list[I]], I] | None = None
    on_enter: Callable[[I], Awaitable[None]] | None = None
    on_exit: Callable[[I, R], Awaitable[None]] | None = None
    queue_capacity: int | None = None  # None means unlimited buffer size


def _default_item_picker(l: list):
    return l.pop(0)


@dataclass
class _Buf:
    item_picker: Callable[[list], Any]
    max_size: int | None = None  # None means unlimited

    _items: list = field(default_factory=list)
    _ev: asyncio.Event = field(default_factory=asyncio.Event)
    _not_full_ev: asyncio.Event = field(default_factory=lambda: asyncio.Event())

    def __post_init__(self):
        # Initially the buffer is not full
        self._not_full_ev.set()

    def full(self) -> bool:
        """Check if buffer is full"""
        if self.max_size is None:
            return False
        return len(self._items) >= self.max_size

    async def push(self, item):
        # Wait until buffer is not full
        while self.full():
            await self._not_full_ev.wait()

        self._items.append(item)
        self._ev.set()

        # Check if buffer became full after adding the item
        if self.full():
            self._not_full_ev.clear()

    async def get(self):
        while True:
            await self._ev.wait()
            if not self._items:
                self._ev.clear()
                continue

            was_full = self.full()
            item = self.item_picker(self._items)

            # If buffer was full and now has space, signal not full
            if was_full and not self.full():
                self._not_full_ev.set()

            if not self._items:
                self._ev.clear()

            return item


@dataclass
class PipelineHandle(Generic[I]):
    push: Callable[[I], Awaitable[None]]
    full: Callable[[], bool]


@contextlib.asynccontextmanager
async def _run_pipeline(
    pipeline: Pipeline[I, R],
):
    done_queue = asyncio.Queue()

    async def _process_done_items():
        while True:
            item = await done_queue.get()
            await pipeline._on_finish(item)

    async with asyncio.TaskGroup() as tg:
        stage_defs = pipeline._stage_defs
        tasks: list[asyncio.Task[Any]] = []
        in_bufs = [
            _Buf(item_picker=stage_def.item_picker or _default_item_picker, max_size=stage_def.queue_capacity)
            for stage_def in stage_defs
        ]  # 各ステージ間を繋ぐパイプ。bufs[0]は最初のステージの入力バッファ
        resolves = [*(in_bufs[i + 1].push for i in range(len(stage_defs) - 1)), done_queue.put]
        for stage_def, in_buf, resolve in zip(stage_defs, in_bufs, resolves):
            for _ in range(stage_def.parallel):
                tasks.append(
                    tg.create_task(
                        _task(
                            _TaskArgs(
                                in_buf=in_buf,
                                process=stage_def.process,
                                on_enter=stage_def.on_enter or _noop_async,
                                on_exit=stage_def.on_exit or _noop_async,
                                resolve=resolve,
                            )
                        )
                    )
                )
        tasks.append(tg.create_task(_process_done_items()))

        def cancel() -> None:
            for task in tasks:
                task.cancel()

        try:
            yield PipelineHandle[I](
                push=in_bufs[0].push,
                full=in_bufs[0].full,
            )
        finally:
            cancel()


@dataclass
class _TaskArgs:
    in_buf: _Buf  # 前のステージからの入力バッファ
    process: Callable[[Any], Awaitable[Any]]  # 各ステージでの処理関数
    on_enter: Callable[[Any], Awaitable[None]]  # 各ステージに入る前の処理
    on_exit: Callable[[Any, Any], Awaitable[None]]  # 各ステージから出る前の処理
    resolve: Callable[[Any], Awaitable[Any] | Any]  # 処理結果の解決


class Skip(Exception):
    pass


async def _task(args: _TaskArgs):
    while True:
        item = await args.in_buf.get()
        try:
            await args.on_enter(item)
            result = await args.process(item)
            await args.on_exit(item, result)
            resolution = args.resolve(result)
            if inspect.isawaitable(resolution):  # pragma: no branch
                await resolution
        except Skip:
            pass
        except asyncio.CancelledError:  # pragma: no cover
            raise
        except Exception as e:  # pragma: no cover
            logger.error(f"Error occurred in pipeline: {e}", exc_info=True)
            pass
