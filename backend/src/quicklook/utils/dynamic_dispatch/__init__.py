"""
動的スケジューリングシステム

複数の性能が異なるWorkerで並列処理を行う際に、
動的に負荷分散とエラーハンドリング、さらに長時間実行タスクの再配置を行うシステム。

各Workerの容量制限を厳密に守り、ラウンドロビン方式で
公平にタスクを分散して実行効率を最大化する。
遅いWorkerによるボトルネックを防ぐため、設定した閾値時間を超えたタスクは
利用可能な高速Workerに自動再配置される。
"""

import asyncio
import time
import statistics
from dataclasses import dataclass
from typing import (
    Any,
    Awaitable,
    Callable,
    Coroutine,
    Generic,
    Iterable,
    TypeVar,
    Sequence,
    AsyncIterator,
)
from collections import deque


# 型変数の定義
Item = TypeVar("Item")
R = TypeVar("R")


class WorkerDownError(Exception):
    """Workerが停止したことを示すエラー"""

    pass


@dataclass(frozen=True)
class Worker(Generic[Item, R]):
    """Workerの設定を表すデータクラス"""
    
    run: Callable[[Item], Coroutine[Any, Any, R]]
    kill: Callable[[], Coroutine[Any, Any, None]]
    capacity: int


@dataclass(frozen=True)
class RunningTaskInfo(Generic[Item, R]):
    """実行中のタスク情報を表すクラス"""
    
    worker: Worker[Item, R]
    item: Item
    start_time: float
    redistribution_count: int = 0  # 再配置回数（たらい回し防止用）


@dataclass(frozen=True)
class Result(Generic[Item, R]):
    """処理結果を表すクラス"""

    item: Item
    worker: Worker[Item, R]
    value: R
    execution_time: float


async def dynamic_dispatch(
    workers: Sequence[Worker[Item, R]],
    items: Iterable[Item],
    *,
    retry_on_worker_down: bool = True,
    on_late_result: Callable[[Result[Item, R]], Awaitable[None]] | None = None,
    max_redistribution_count: int = 1,
) -> AsyncIterator[Result[Item, R]]:
    """動的スケジューリングでアイテムを処理する

    Args:
        workers: 処理を行うWorkerのリスト
        items: 処理対象のアイテム
        retry_on_worker_down: Workerが停止した場合に再試行するかどうか
        on_late_result: 遅延結果のコールバック関数
        max_redistribution_count: 1つのアイテムの最大再配置回数（たらい回し防止）

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
    running_tasks: dict[asyncio.Task[R], RunningTaskInfo[Item, R]] = {}

    # 完了したタスクの実行時間を追跡（再配置判定のため）
    completed_execution_times: list[float] = []

    # 停止したWorkerを管理
    dead_workers: set[Worker[Item, R]] = set()

    # 全タスク完了フラグ
    all_items_scheduled = False

    # Workerごとの実行中タスク数を管理（容量制限を正確に守るため）
    worker_running_count: dict[Worker[Item, R], int] = {worker: 0 for worker in workers}

    # 利用可能なWorkerを取得（容量に余裕があり、停止していないWorker）
    def get_available_workers() -> list[Worker[Item, R]]:
        return [w for w in workers if w not in dead_workers and worker_running_count[w] < w.capacity]

    # Workerの現在の空き容量を計算
    def get_worker_available_capacity(worker: Worker[Item, R]) -> int:
        if worker in dead_workers:
            return 0
        return max(0, worker.capacity - worker_running_count[worker])

    # タスクを新規作成してWorkerに割り当て
    def create_task(worker: Worker[Item, R], item: Item, redistribution_count: int = 0) -> asyncio.Task[R]:
        start_time = time.time()
        task = asyncio.create_task(worker.run(item))
        running_tasks[task] = RunningTaskInfo(
            worker=worker, 
            item=item, 
            start_time=start_time,
            redistribution_count=redistribution_count
        )
        # ワーカーの実行中タスク数を増やして容量制限を管理
        worker_running_count[worker] += 1
        return task

    # 利用可能なWorkerに新しいタスクをスケジュール
    def schedule_new_tasks() -> None:
        """
        待機中のアイテムを利用可能なWorkerに割り当てる。
        各Workerの容量制限を厳密に守り、ラウンドロビン方式で負荷分散を行う。
        """
        while pending_items:
            # 容量に余裕のあるワーカーがない場合は終了
            if not any(get_worker_available_capacity(w) > 0 for w in workers if w not in dead_workers):
                break
            
            # この反復でタスクが割り当てられたかどうかを追跡
            tasks_assigned = False
            
            # 全ワーカーに対してラウンドロビン方式でタスクを割り当て
            for worker in workers:
                if worker in dead_workers:
                    continue
                    
                # このワーカーの現在の容量をチェック
                available_capacity = get_worker_available_capacity(worker)
                if available_capacity > 0 and pending_items:
                    item = pending_items.popleft()
                    create_task(worker, item)
                    tasks_assigned = True
                    # 公平な負荷分散のため、1つのアイテムを割り当てた後、次のワーカーに移る
                
            # 何もタスクが割り当てられなかった場合は終了
            if not tasks_assigned:
                break

    # アイテムが空になった時に実行中のタスクを高速Workerに再配置する
    def redistribute_running_tasks() -> None:
        """
        新規アイテムが空になった時点で、実行中のタスクを利用可能な高速Workerに再配置する。
        
        完了したタスクの実行時間の中央値の2倍を超えているタスクのみを再配置対象とし、
        最も古いタスクから順に処理する。これにより、遅いWorkerに割り当てられたタスクによる
        全体的な遅延を防ぐ。無限たらい回しを防ぐため、各アイテムには最大再配置回数の制限がある。
        """
        # 新しいアイテムが待機中の場合は再配置しない（新規アイテムを優先）
        if pending_items:
            return
            
        # 実行中のタスクがない場合は何もしない
        if not running_tasks:
            return
            
        # 利用可能なWorkerを取得（空き容量がある）
        available_workers = [w for w in get_available_workers() if get_worker_available_capacity(w) > 0]
        
        if not available_workers:
            return
        
        # 完了したタスクの実行時間の中央値を計算
        median_execution_time = 0.0
        if completed_execution_times:
            median_execution_time = statistics.median(completed_execution_times)
        
        # 中央値の2倍を閾値とする
        redistribution_threshold = median_execution_time * 2.0
        current_time = time.time()
        
        # 再配置可能なタスクを特定（中央値の2倍を超える実行時間で、最大再配置回数に達していない）
        redistributable_tasks = []
        for task, task_info in running_tasks.items():
            if (not task.cancelled() and 
                task_info.redistribution_count < max_redistribution_count and
                (current_time - task_info.start_time) > redistribution_threshold):
                redistributable_tasks.append((task, task_info))
        
        if not redistributable_tasks:
            return
        
        # 最も古いタスクから順に並び替え（start_time昇順）
        redistributable_tasks.sort(key=lambda x: x[1].start_time)
        
        # すべての実行中タスクの中で、より高速なWorkerに移せるものを処理
        redistributed_count = 0
        for task, task_info in redistributable_tasks:
            if not available_workers:
                break
                
            # 最も空き容量の大きいWorkerを選択
            best_worker = max(available_workers, key=get_worker_available_capacity)
            
            # 同じWorkerの場合は再配置しない
            if best_worker == task_info.worker:
                continue
            
            # 元のタスクをキャンセルして新しいWorkerで再実行
            task.cancel()
            running_tasks.pop(task, None)
            worker_running_count[task_info.worker] -= 1
            
            # 新しいWorkerで同じアイテムを再実行（再配置回数を増やす）
            create_task(
                best_worker, 
                task_info.item, 
                redistribution_count=task_info.redistribution_count + 1
            )
            redistributed_count += 1
            
            # 利用可能なWorkerリストを更新
            if get_worker_available_capacity(best_worker) == 0:
                available_workers.remove(best_worker)

    # 初期タスクをスケジュール
    schedule_new_tasks()

    # アイテムがすべてスケジュールされたかチェック
    if not pending_items:
        all_items_scheduled = True

    # メインループ
    while running_tasks or pending_items:
        if not running_tasks:
            # 実行中のタスクがないが、未処理アイテムがある場合
            if not any(get_worker_available_capacity(w) > 0 for w in workers if w not in dead_workers):
                if not retry_on_worker_down:
                    # 利用可能なWorkerがなく、再試行も無効の場合は終了
                    break
                # 少し待ってから再試行
                await asyncio.sleep(0.1)
                continue
            schedule_new_tasks()
            continue

        # タスク再配置を試行（アイテムが空になった時のみ）
        if not pending_items:
            redistribute_running_tasks()

        # 完了したタスクを待機
        done, pending_wait = await asyncio.wait(
            running_tasks.keys(), 
            return_when=asyncio.FIRST_COMPLETED,
            timeout=0.1  # 0.1秒ごとに再配置をチェック
        )
            
        if not done:
            # タイムアウトした場合は次のループで再配置を再チェック
            continue

        for task in done:
            task_info = running_tasks.pop(task, None)
            if task_info is None:
                continue  # キャンセルされたタスクは無視
                
            # ワーカーの実行中タスク数を減らして容量を解放
            worker_running_count[task_info.worker] -= 1

            try:
                if task.cancelled():
                    # キャンセルされたタスクは処理しない
                    continue
                    
                result_value = await task
                execution_time = time.time() - task_info.start_time
                
                # 完了したタスクの実行時間を記録（再配置判定のため）
                completed_execution_times.append(execution_time)
                
                result = Result(item=task_info.item, worker=task_info.worker, value=result_value, execution_time=execution_time)
                yield result

                # 遅延結果のコールバック判定
                if on_late_result is not None and all_items_scheduled and not pending_items and not running_tasks:
                    await on_late_result(result)

            except WorkerDownError:
                # Workerが停止した場合
                dead_workers.add(task_info.worker)
                await task_info.worker.kill()

                if retry_on_worker_down:
                    # 再試行が有効な場合、失敗したアイテムを戻す
                    pending_items.appendleft(task_info.item)
                # retry_on_worker_down=Falseの場合は何もしない（アイテムは失われる）
            except asyncio.CancelledError:
                # キャンセルされたタスクは無視（再配置済み）
                pass

        # 新しいタスクをスケジュール
        schedule_new_tasks()

        # アイテムがすべてスケジュールされたかチェック
        if not pending_items and not all_items_scheduled:
            all_items_scheduled = True
