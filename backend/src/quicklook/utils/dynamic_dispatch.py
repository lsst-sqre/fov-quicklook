"""
動的スケジューリングシステム

複数の性能が異なるWorkerで並列処理を行う際に、
動的に負荷分散とエラーハンドリングを行うシステムです。
"""

import asyncio
import time
from dataclasses import dataclass
from typing import (
    Any,
    Awaitable,
    Callable,
    Generic,
    Iterable,
    Protocol,
    TypeVar,
    Sequence,
    AsyncIterator,
)
from collections import deque


# 型変数の定義
Item = TypeVar("Item")
R = TypeVar("R")
# Protocolの型変数（適切な変性を設定）
Item_contra = TypeVar("Item_contra", contravariant=True)
R_co = TypeVar("R_co", covariant=True)


class WorkerDownError(Exception):
    """Workerが停止したことを示すエラー"""

    pass


@dataclass(frozen=True)
class Result(Generic[Item, R]):
    """処理結果を表すクラス"""

    item: Item
    worker: "Worker[Item, R]"
    value: R
    execution_time: float


class Worker(Protocol, Generic[Item_contra, R_co]):
    """Workerのプロトコル定義"""

    def capacity(self) -> int:
        """現在処理可能なアイテム数を返す"""
        ...

    async def run(self, item: Item_contra) -> R_co:
        """アイテムの処理を実行する

        Args:
            item: 処理対象のアイテム

        Returns:
            処理結果

        Raises:
            WorkerDownError: Workerが停止している場合
        """
        ...

    async def kill(self) -> None:
        """Workerを停止する"""
        ...


async def dynamic_dispatch(
    workers: Sequence[Worker[Item, R]],
    items: Iterable[Item],
    *,
    retry_on_worker_down: bool = True,
    on_late_result: Callable[[Result[Item, R]], Awaitable[None]] | None = None,
) -> AsyncIterator[Result[Item, R]]:
    """動的スケジューリングでアイテムを処理する

    Args:
        workers: 処理を行うWorkerのリスト
        items: 処理対象のアイテム
        retry_on_worker_down: Workerが停止した場合に再試行するかどうか
        on_late_result: 遅延結果のコールバック関数

    Returns:
        処理結果のリスト

    Raises:
        ValueError: 利用可能なWorkerがない場合
    """
    if not workers:
        raise ValueError("少なくとも1つのWorkerが必要です")

    # 処理待ちのアイテムキュー
    pending_items = deque(items)

    # 処理中のタスクを管理
    running_tasks: dict[asyncio.Task[R], tuple[Worker[Item, R], Item, float]] = {}

    # 停止したWorkerを管理
    dead_workers: set[Worker[Item, R]] = set()

    # 全タスク完了フラグ
    all_items_scheduled = False

    # 利用可能なWorkerを取得
    def get_available_workers() -> list[Worker[Item, R]]:
        return [w for w in workers if w not in dead_workers and w.capacity() > 0]

    # タスクを新規作成
    def create_task(worker: Worker[Item, R], item: Item) -> asyncio.Task[R]:
        start_time = time.time()
        task = asyncio.create_task(worker.run(item))
        running_tasks[task] = (worker, item, start_time)
        return task

    # 新しいタスクをスケジュール
    def schedule_new_tasks() -> None:
        available_workers = get_available_workers()

        for worker in available_workers:
            while worker.capacity() > 0 and pending_items:
                item = pending_items.popleft()
                create_task(worker, item)
                break  # 1つずつ確実に割り当て

    # 初期タスクをスケジュール
    schedule_new_tasks()

    # アイテムがすべてスケジュールされたかチェック
    if not pending_items:
        all_items_scheduled = True

    # メインループ
    while running_tasks or pending_items:
        if not running_tasks:
            # 実行中のタスクがないが、未処理アイテムがある場合
            available_workers = get_available_workers()
            if not available_workers:
                if not retry_on_worker_down:
                    # 利用可能なWorkerがなく、再試行も無効の場合は終了
                    break
                # 少し待ってから再試行
                await asyncio.sleep(0.1)
                continue
            schedule_new_tasks()
            continue

        # 完了したタスクを待機
        done, pending = await asyncio.wait(running_tasks.keys(), return_when=asyncio.FIRST_COMPLETED)

        for task in done:
            worker, item, start_time = running_tasks.pop(task)

            try:
                result_value = await task
                execution_time = time.time() - start_time
                result = Result(item=item, worker=worker, value=result_value, execution_time=execution_time)
                yield result

                # 遅延結果のコールバック判定
                if on_late_result is not None and all_items_scheduled and not pending_items and not running_tasks:
                    await on_late_result(result)

            except WorkerDownError:
                # Workerが停止した場合
                dead_workers.add(worker)
                await worker.kill()

                if retry_on_worker_down:
                    # 再試行が有効な場合、失敗したアイテムを戻す
                    pending_items.appendleft(item)
                # retry_on_worker_down=Falseの場合は何もしない（アイテムは失われる）

        # 新しいタスクをスケジュール
        schedule_new_tasks()

        # アイテムがすべてスケジュールされたかチェック
        if not pending_items and not all_items_scheduled:
            all_items_scheduled = True
