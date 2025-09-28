"""
Adaptive Map - 動的負荷分散による並列処理

複数のWorkerに対してItemsを動的に割り当てて並列処理を行う。
各Workerの性能差を考慮し、遅いWorkerがボトルネックにならないよう
リスケジューリング機能を提供する。
"""

import asyncio
import statistics
import time
from abc import ABC, abstractmethod
from collections import deque
from dataclasses import dataclass
from typing import Any, AsyncIterator, Awaitable, Callable, Sequence


class WorkerDown(Exception):
    """Workerが停止したことを示す例外"""

    pass


class Worker(ABC):
    """
    並列処理を行うWorkerの抽象クラス

    Workerのライフサイクルは呼び出し元が管理する。
    adaptive_mapは単純にWorkerを使用するだけで、Workerの生成や
    teardownは呼び出し元の責任である。
    """

    @abstractmethod
    def id(self) -> str:
        """workerを識別する文字列。内部では使わない。ユーザー用"""
        ...

    @abstractmethod
    def capacity(self) -> int:
        """現在のsubmitの受付可能な処理数を返す"""
        ...

    @abstractmethod
    async def submit(self, item: Any) -> Any:
        """workerにitemの処理を依頼する"""
        ...

    @abstractmethod
    async def wait_until_available(self) -> None:
        """workerが利用可能になるまでブロック"""
        ...

    @abstractmethod
    async def teardown(self) -> None:
        """
        ワーカーをクリーンアップする

        注意: adaptive_mapは自動的にteardownを呼び出さない。
        WorkerDownが発生した場合、呼び出し元がteardownの実行を検討する。
        """
        ...


class _HelperWorker(Worker):
    """ヘルパー関数で作成されるWorker実装"""

    def __init__(
        self,
        *,
        id: str,
        max_concurrency: int,
        process_item: Callable[[Any], Awaitable[Any]],
        teardown_func: Callable[[], Awaitable[None]],
    ):
        self._id = id
        self._max_concurrency = max_concurrency
        self._process_item = process_item
        self._teardown_func = teardown_func
        self._current_capacity = max_concurrency
        self._shutdown = False
        self._lock = asyncio.Lock()
        self._capacity_changed = asyncio.Event()
        self._capacity_changed.set()  # 初期状態では利用可能

    def capacity(self) -> int:
        if self._shutdown:  # pragma: no cover
            return 0
        return self._current_capacity

    async def submit(self, item: Any) -> Any:
        while True:
            async with self._lock:
                if self._shutdown:  # pragma: no cover
                    raise RuntimeError("Worker is shutdown")

                if self._current_capacity > 0:
                    self._current_capacity -= 1
                    if self._current_capacity == 0:  # pragma: no branch
                        self._capacity_changed.clear()
                    break

            await self._capacity_changed.wait()

        try:
            result = await self._process_item(item)
            return result
        finally:
            async with self._lock:
                # capacityを増やす
                self._current_capacity += 1
                if self._current_capacity > 0:  # pragma: no branch
                    self._capacity_changed.set()

    async def wait_until_available(self) -> None:
        while not self._shutdown:  # pragma: no branch
            if self._current_capacity > 0:
                break
            await self._capacity_changed.wait()

    async def teardown(self) -> None:
        self._shutdown = True
        self._capacity_changed.set()  # 待機中のwait_until_availableを解除
        await self._teardown_func()

    def id(self):
        return self._id


async def _noop_teardown() -> None:
    """デフォルトのteardown"""
    return None


def create_worker(
    id: str,
    process_item: Callable[[Any], Awaitable[Any]],
    *,
    max_concurrency: int = 1,
    teardown: Callable[[], Awaitable[None]] | None = None,
) -> Worker:
    """
    teardown、max_concurrency、submitからWorkerを作成するヘルパー関数

    作成されるWorkerは以下の特徴を持つ：
    - submitされると自動的にcapacityを減らし、process_itemを実行し、実行が終わればcapacityを増やす
    - wait_until_availableの実装：submitされた処理が終わったタイミングでcapacityが0以上になっていたらブロックを解除

    Args:
        process_item: itemを処理する非同期関数
        max_concurrency: 最大同時実行数
        teardown: ワーカーをクリーンアップする非同期関数

    Returns:
        Worker: 作成されたWorker
    """
    if max_concurrency <= 0:
        raise ValueError("max_concurrency must be positive")

    teardown_func = teardown if teardown is not None else _noop_teardown
    return _HelperWorker(
        id=id,
        max_concurrency=max_concurrency,
        process_item=process_item,
        teardown_func=teardown_func,
    )


@dataclass
class MapResult:
    """adaptive_mapの処理結果"""

    worker: Worker
    item: Any
    value: Any
    execution_time: float


@dataclass(slots=True)
class _ItemEntry:
    """処理待ちアイテムのメタ情報"""

    index: int
    value: Any


@dataclass
class _RunningTask:
    """実行中のタスクの情報"""

    worker: Worker
    item: Any
    item_index: int
    task: asyncio.Task
    start_time: float
    rescheduled: bool = False


class _AdaptiveMapRunner:
    """
    adaptive_mapの実装クラス

    テストしやすさを考慮して、単一の巨大な関数から
    責任を分離したクラス構造に変更。
    """

    def __init__(
        self,
        workers: Sequence[Worker],
        items: Sequence[Any],
        *,
        on_late_result: Callable[[MapResult], None] | None = None,
        cancel_on_reschedule: bool = True,
        reschedule_threshold_multiplier: float = 2.0,
    ):
        self.workers = workers
        self.remaining_items = deque(_ItemEntry(index, item) for index, item in enumerate(list(items)))
        self.on_late_result = on_late_result
        self.cancel_on_reschedule = cancel_on_reschedule
        self.reschedule_threshold_multiplier = reschedule_threshold_multiplier

        self.running_tasks: dict[asyncio.Task, _RunningTask] = {}
        self.completed_execution_times: list[float] = []
        self.yielded_item_indexes: set[int] = set()
        self.failed_workers: set[Worker] = set()

    async def run(self) -> AsyncIterator[MapResult]:
        """メインの処理ループを実行"""
        if not self.workers and not self.remaining_items:
            return

        if len(self.workers) == 0:
            raise ValueError("No available workers")

        try:
            while self.remaining_items or self.running_tasks:
                # 新しいitemをsubmitする
                await self._submit_new_tasks()

                if not self.running_tasks:  # pragma: no cover
                    break

                # タスク完了を待つ
                done_tasks, _ = await asyncio.wait(list(self.running_tasks.keys()), return_when=asyncio.FIRST_COMPLETED)

                # 完了したタスクを処理
                for task in done_tasks:
                    map_result = await self._handle_completed_task(task)
                    if map_result is not None:
                        yield map_result

                # リスケジューリングの判定
                await self._handle_rescheduling()

        finally:
            # 残りのタスクをキャンセル
            for task in self.running_tasks:
                if not task.done():
                    task.cancel()

    async def _submit_new_tasks(self) -> None:
        """新しいitemをsubmitする"""
        while self.remaining_items:
            available_workers = self._get_available_workers()
            if not available_workers:
                break  # 利用可能なworkerがない場合はタスク完了を待つ

            best_worker = self._select_best_worker(available_workers)
            entry = self.remaining_items.popleft()
            item = entry.value
            item_index = entry.index
            start_time = time.time()

            # submit用のコルーチンを作成
            submit_coro = best_worker.submit(item)
            task = asyncio.create_task(submit_coro)
            running_task = _RunningTask(worker=best_worker, item=item, item_index=item_index, task=task, start_time=start_time)
            self.running_tasks[task] = running_task

            # capacityが確実に更新されるように少し待つ
            await asyncio.sleep(0)  # イベントループに制御を戻す

    async def _handle_completed_task(self, task: asyncio.Task) -> MapResult | None:
        """完了したタスクを処理し、必要に応じてMapResultを返す"""
        running_task = self.running_tasks.pop(task)

        try:
            result = await task
            execution_time = time.time() - running_task.start_time

            map_result = MapResult(worker=running_task.worker, item=running_task.item, value=result, execution_time=execution_time)

            if running_task.item_index not in self.yielded_item_indexes:
                # 初回完了の場合
                self.yielded_item_indexes.add(running_task.item_index)
                self.completed_execution_times.append(execution_time)
                return map_result
            elif self.on_late_result:  # pragma: no branch
                # 遅延結果の場合
                self.on_late_result(map_result)

        except WorkerDown:
            # Workerが停止した場合、失敗したWorkerとして記録
            self.failed_workers.add(running_task.worker)
            # itemをリスケジュール
            if running_task.item_index not in self.yielded_item_indexes:  # pragma: no branch
                self.remaining_items.appendleft(_ItemEntry(running_task.item_index, running_task.item))

        return None

    async def _handle_rescheduling(self) -> None:
        """リスケジューリングの判定と実行"""
        if self.remaining_items or not self.running_tasks:
            return

        threshold = self._calculate_reschedule_threshold()
        tasks_to_reschedule = self._find_tasks_to_reschedule(threshold)

        for task, running_task in tasks_to_reschedule:
            await self._reschedule_task(task, running_task)

    async def _reschedule_task(self, task: asyncio.Task, running_task: _RunningTask) -> None:
        """単一のタスクをリスケジュールする"""
        available_workers = self._get_available_workers()
        if not available_workers:
            return

        best_worker = self._select_best_worker(available_workers)
        if best_worker == running_task.worker:
            return

        try:
            # 新しいタスクを作成
            new_task = asyncio.create_task(best_worker.submit(running_task.item))
            new_running_task = _RunningTask(
                worker=best_worker,
                item=running_task.item,
                item_index=running_task.item_index,
                task=new_task,
                start_time=time.time(),
                rescheduled=True,
            )
            self.running_tasks[new_task] = new_running_task

            # 元のタスクをリスケジュール済みとしてマーク
            running_task.rescheduled = True

            # 必要に応じて元のタスクをキャンセル
            if self.cancel_on_reschedule:
                task.cancel()

        except WorkerDown:  # pragma: no cover
            self.failed_workers.add(best_worker)

    def _find_tasks_to_reschedule(self, threshold: float) -> list[tuple[asyncio.Task, _RunningTask]]:
        """リスケジュール対象のタスクを見つける"""
        current_time = time.time()
        tasks_to_reschedule = []

        for task, running_task in self.running_tasks.items():
            if not running_task.rescheduled and current_time - running_task.start_time > threshold:
                tasks_to_reschedule.append((task, running_task))

        return tasks_to_reschedule

    def _calculate_reschedule_threshold(self) -> float:
        """リスケジュール判定の閾値を計算"""
        if self.completed_execution_times:
            median_time = statistics.median(self.completed_execution_times)
        else:
            median_time = 0.0
        return median_time * self.reschedule_threshold_multiplier

    def _select_best_worker(self, available_workers: Sequence[Worker]) -> Worker:
        """capacity最大のworkerを選択"""
        return max(available_workers, key=lambda w: w.capacity())

    def _get_available_workers(self) -> list[Worker]:
        """利用可能なWorkerのリストを取得"""
        return [w for w in self.workers if w not in self.failed_workers and w.capacity() > 0]


async def adaptive_map(
    workers: Sequence[Worker],
    items: Sequence[Any],
    *,
    on_late_result: Callable[[MapResult], None] | None = None,
    cancel_on_reschedule: bool = True,
    reschedule_threshold_multiplier: float = 2.0,
) -> AsyncIterator[MapResult]:
    """
    動的負荷分散による並列処理を行う

    注意: この関数はWorkerのライフサイクルを管理しない。
    Workerの生成とteardownは呼び出し元の責任である。
    WorkerDownが発生した場合、該当するWorkerは以降使用されなくなるが、
    teardownは自動的に呼び出されない。

    Args:
        workers: 処理を行うWorkerのリスト
        items: 処理対象のアイテムリスト
        on_late_result: 遅延結果のコールバック関数
        cancel_on_reschedule: リスケジュール時に元のタスクをキャンセルするか
        reschedule_threshold_multiplier: リスケジュールの閾値倍率

    Yields:
        MapResult: 処理結果
    """
    runner = _AdaptiveMapRunner(
        workers,
        items,
        on_late_result=on_late_result,
        cancel_on_reschedule=cancel_on_reschedule,
        reschedule_threshold_multiplier=reschedule_threshold_multiplier,
    )

    async for result in runner.run():
        yield result


__all__ = ['Worker', 'WorkerDown', 'MapResult', 'adaptive_map', 'create_worker']
