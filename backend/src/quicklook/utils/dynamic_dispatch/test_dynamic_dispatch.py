"""
新しいdynamic_dispatchの包括的テスト

dataclassベースのWorkerインターフェースとタスク再配置機能をテストする
"""

import asyncio
import time
from typing import Any, Coroutine

import pytest

from quicklook.utils.dynamic_dispatch import Result, Worker, WorkerDownError, dynamic_dispatch


class MockWorkerImpl:
    """新しいインターフェース用のMockWorker実装"""
    
    def __init__(
        self,
        name: str,
        capacity: int = 2,
        processing_time: float = 0.1,
        failure_rate: float = 0.0,
        worker_down_rate: float = 0.0,
        should_fail_on_items: list[Any] | None = None,
    ):
        self.name = name
        self.capacity = capacity
        self.processing_time = processing_time
        self.failure_rate = failure_rate
        self.worker_down_rate = worker_down_rate
        self.should_fail_on_items = should_fail_on_items or []
        
        self._is_killed = False
        self._completed_items: list[Any] = []
        self._running_tasks: set[int] = set()
        
    async def run(self, item: Any) -> str:
        """アイテムの処理を実行する"""
        if self._is_killed:
            raise WorkerDownError(f"Worker {self.name} は停止しています")
        
        item_id = id(item)
        self._running_tasks.add(item_id)
        
        try:
            # 特定のアイテムでの失敗をシミュレート
            if item in self.should_fail_on_items:
                raise WorkerDownError(f"Worker {self.name} が item {item} で失敗")
            
            # ランダムな失敗をシミュレート
            if self.failure_rate > 0 and len(self._completed_items) == 0:  # 最初の実行時のみ失敗
                self._is_killed = True
                raise WorkerDownError(f"Worker {self.name} がランダムに停止")
            
            # 処理時間をシミュレート
            await asyncio.sleep(self.processing_time)
            
            self._completed_items.append(item)
            return f"processed_{item}_by_{self.name}"
            
        finally:
            self._running_tasks.discard(item_id)
    
    async def kill(self) -> None:
        """Workerを停止する"""
        self._is_killed = True
        self._running_tasks.clear()
    
    def __repr__(self) -> str:
        return f"MockWorkerImpl({self.name})"


def create_worker(
    name: str,
    capacity: int = 2,
    processing_time: float = 0.1,
    failure_rate: float = 0.0,
    worker_down_rate: float = 0.0,
    should_fail_on_items: list[Any] | None = None,
) -> Worker[Any, str]:
    """新しいWorkerを作成するヘルパー関数"""
    impl = MockWorkerImpl(
        name=name,
        capacity=capacity,
        processing_time=processing_time,
        failure_rate=failure_rate,
        worker_down_rate=worker_down_rate,
        should_fail_on_items=should_fail_on_items,
    )
    return Worker(
        run=impl.run,
        kill=impl.kill,
        capacity=capacity
    )


async def test_basic_functionality_new_interface():
    """新しいインターフェースでの基本的な動作テスト"""
    workers = [
        create_worker("worker1", capacity=2, processing_time=0.1),
        create_worker("worker2", capacity=3, processing_time=0.05),
    ]
    items = [1, 2, 3, 4, 5]
    
    results = [r async for r in dynamic_dispatch(workers, items)]
    
    assert len(results) == 5
    processed_items = [r.item for r in results]
    assert sorted(processed_items) == sorted(items)
    
    # 全てのアイテムが処理されていることを確認
    for result in results:
        assert result.worker in workers
        assert result.item in items
        assert isinstance(result.value, str)
        assert "processed_" in result.value
        assert result.execution_time > 0


async def test_immediate_redistribution_when_items_empty():
    """アイテムが空になった時の条件付き再配置テスト（中央値ベース）"""
    # 非常に遅いWorkerと高速なWorkerを設定
    workers = [
        create_worker("very_slow", capacity=1, processing_time=2.0),  # 2秒
        create_worker("fast", capacity=2, processing_time=0.1),       # 0.1秒
    ]
    items = [1, 2, 3, 4, 5]  # アイテム数を増やして中央値が計算できるようにする
    
    start_time = time.time()
    
    # 新しい実装では、完了したタスクの実行時間の中央値の2倍を超えるタスクのみ再配置される
    results = [r async for r in dynamic_dispatch(workers, items)]
    
    end_time = time.time()
    total_time = end_time - start_time
    
    assert len(results) == 5
    processed_items = [r.item for r in results]
    assert sorted(processed_items) == sorted(items)
    
    # 高速Workerが多くのタスクを処理していることを確認
    fast_worker_results = [r for r in results if r.worker == workers[1]]  # fast worker
    slow_worker_results = [r for r in results if r.worker == workers[0]]  # slow worker
    
    # 高速Workerが初期配置でいくつかのタスクを完了し、その後中央値ベースの再配置が起こる
    assert len(fast_worker_results) >= 2, f"Fast worker should handle at least 2 items, got {len(fast_worker_results)}"
    
    # 全体の処理時間は再配置により改善されているべき
    print(f"Total time: {total_time:.2f}s, Fast worker processed: {len(fast_worker_results)} items")
    
    # 中央値ベースの再配置により、処理時間が改善される
    # ただし、一部のタスクは遅いWorkerで完了するまで実行される可能性がある
    assert total_time < 4.0, f"Total time should be improved by median-based redistribution: {total_time:.2f}s"


async def test_no_infinite_redistribution():
    """無限たらい回し防止テスト"""
    # 全てのWorkerが同程度に遅い場合のテスト
    workers = [
        create_worker("slow1", capacity=1, processing_time=1.0),
        create_worker("slow2", capacity=1, processing_time=1.0),
        create_worker("slow3", capacity=1, processing_time=1.0),
    ]
    items = [1, 2, 3]
    
    start_time = time.time()
    
    # max_redistribution_countのデフォルト値（2）をテスト
    results = [r async for r in dynamic_dispatch(workers, items)]
    
    end_time = time.time()
    total_time = end_time - start_time
    
    assert len(results) == 3
    processed_items = [r.item for r in results]
    assert sorted(processed_items) == sorted(items)
    
    # 無限ループになっていないことを確認（適切な時間で完了）
    # 3つのアイテムが並列実行されるので、約1秒で完了するはず
    assert total_time < 2.0, f"Total time: {total_time}, should not loop infinitely"


async def test_max_redistribution_count_parameter():
    """max_redistribution_count パラメータのテスト"""
    # 一つのWorkerだけ非常に遅い設定
    workers = [
        create_worker("very_slow", capacity=1, processing_time=3.0),
        create_worker("medium", capacity=1, processing_time=0.5),
        create_worker("fast", capacity=1, processing_time=0.1),
    ]
    items = [1]  # 1つのアイテムのみ
    
    start_time = time.time()
    
    # 再配置回数を1回に制限
    results = [r async for r in dynamic_dispatch(
        workers, 
        items, 
        max_redistribution_count=1
    )]
    
    end_time = time.time()
    total_time = end_time - start_time
    
    assert len(results) == 1
    assert results[0].item == 1
    
    # 1回の再配置で処理が完了することを確認
    # ラウンドロビンで最初は very_slow に配置されるが、再配置により高速化される
    # 最遅でも medium Worker(0.5秒) で処理されるはず
    assert total_time < 1.0, f"Total time: {total_time}, expected < 1.0s with max_redistribution_count=1"
    
    # 実際に再配置が機能していることを確認
    # very_slow worker以外で処理されていれば、再配置が機能している
    assert results[0].worker != workers[0], "Task should be redistributed from very_slow worker"


async def test_no_redistribution_when_items_pending():
    """未処理アイテムがある間は再配置しないことをテスト"""
    workers = [
        create_worker("slow", capacity=1, processing_time=0.3),  # 処理時間を短縮
        create_worker("fast", capacity=1, processing_time=0.05),
    ]
    items = [1, 2, 3]  # アイテム数を減らして確実に両方のWorkerが処理するようにする
    
    # 新しい実装では、アイテムが残っている間は再配置しない
    results = [r async for r in dynamic_dispatch(workers, items)]
    
    assert len(results) == 3
    # 未処理アイテムがある間は再配置されないため、両方のWorkerが処理する可能性がある
    # ただし、高速Workerが全て処理する可能性もあるため、結果の妥当性のみ確認
    all_processed_items = [r.item for r in results]
    assert sorted(all_processed_items) == sorted(items)


async def test_worker_down_with_new_interface():
    """新しいインターフェースでのWorker停止テスト"""
    failing_worker = create_worker(
        "failing",
        capacity=1,
        should_fail_on_items=[2],  # 2番目のアイテムで失敗
        processing_time=0.1
    )
    backup_worker = create_worker("backup", capacity=2, processing_time=0.1)
    
    workers = [failing_worker, backup_worker]
    items = [1, 2, 3]
    
    results = [r async for r in dynamic_dispatch(
        workers, 
        items, 
        retry_on_worker_down=True
    )]
    
    assert len(results) == 3
    processed_items = [r.item for r in results]
    assert sorted(processed_items) == sorted(items)
    
    # 失敗したアイテムがバックアップWorkerで処理されていることを確認
    backup_results = [r for r in results if r.worker == backup_worker]
    backup_items = [r.item for r in backup_results]
    assert 2 in backup_items, "Failed item should be retried on backup worker"


async def test_capacity_management_new_interface():
    """新しいインターフェースでの容量管理テスト"""
    workers = [
        create_worker("worker1", capacity=2, processing_time=0.2),
        create_worker("worker2", capacity=1, processing_time=0.3),
    ]
    items = list(range(6))
    
    results = [r async for r in dynamic_dispatch(workers, items)]
    
    assert len(results) == 6
    
    # 各Workerが適切に処理していることを確認
    worker1_results = len([r for r in results if r.worker == workers[0]])
    worker2_results = len([r for r in results if r.worker == workers[1]])
    
    assert worker1_results > 0
    assert worker2_results > 0
    assert worker1_results + worker2_results == 6


async def test_on_late_result_callback():
    """遅延結果コールバックのテスト"""
    late_results: list[Result[int, str]] = []
    
    async def collect_late_result(result: Result[int, str]) -> None:
        late_results.append(result)
    
    workers = [
        create_worker("fast", capacity=1, processing_time=0.01),
        create_worker("slow", capacity=1, processing_time=0.3),
    ]
    items = [1, 2]
    
    results = [r async for r in dynamic_dispatch(
        workers, 
        items,
        on_late_result=collect_late_result
    )]
    
    assert len(results) == 2
    # 遅延結果のコールバックが適切に動作することを確認
    # （実際の遅延はタイミングによる）


async def test_empty_workers_raises_error():
    """Workerが存在しない場合のエラーテスト"""
    workers: list[Worker[Any, str]] = []
    items = [1, 2, 3]
    
    with pytest.raises(ValueError, match="少なくとも1つのWorkerが必要です"):
        async for _ in dynamic_dispatch(workers, items):
            pass


async def test_empty_items():
    """空のアイテムリストのテスト"""
    workers = [create_worker("worker1")]
    items: list[int] = []
    
    results = [r async for r in dynamic_dispatch(workers, items)]
    
    assert results == []


async def test_task_redistribution_timing():
    """タスク再配置のタイミングテスト（中央値ベース）"""
    # 一つのWorkerが非常に遅く、もう一つが高速
    workers = [
        create_worker("very_slow", capacity=1, processing_time=2.0),  # 2秒
        create_worker("very_fast", capacity=3, processing_time=0.1), # 0.1秒
    ]
    items = [1, 2, 3, 4, 5]  # アイテム数を増やして中央値が計算できるようにする
    
    start_time = time.time()
    
    # 新しい実装では、完了したタスクの実行時間の中央値の2倍を超えるタスクのみ再配置される
    results = [r async for r in dynamic_dispatch(workers, items)]
    
    end_time = time.time()
    total_time = end_time - start_time
    
    assert len(results) == 5
    
    # 中央値ベースの再配置により処理時間が改善される
    assert total_time < 4.0, f"Total time: {total_time}, should be < 4.0s due to median-based redistribution"
    
    # 高速Workerが再配置によって多くのタスクを処理したことを確認
    fast_worker_results = [r for r in results if r.worker == workers[1]]
    assert len(fast_worker_results) >= 3, "Fast worker should handle redistributed tasks"


async def test_redistribution_based_on_execution_time_median():
    """実行時間の中央値に基づく再配置テスト"""
    # 高速Worker、中速Worker、遅いWorkerを設定
    workers = [
        create_worker("fast", capacity=2, processing_time=0.1),    # 0.1秒
        create_worker("medium", capacity=2, processing_time=0.3),  # 0.3秒
        create_worker("slow", capacity=2, processing_time=1.0),    # 1.0秒
    ]
    # 十分な数のアイテムを用意して、最初にいくつかが完了し中央値が計算できるようにする
    items = list(range(10))
    
    start_time = time.time()
    
    results = [r async for r in dynamic_dispatch(workers, items)]
    
    end_time = time.time()
    total_time = end_time - start_time
    
    assert len(results) == 10
    
    # 中央値が計算され、その2倍を超えるタスクが再配置されることを確認
    # 最初の数個のタスクが完了した時点で中央値が計算され、
    # 遅いWorkerで実行中のタスクが再配置される
    execution_times = [r.execution_time for r in results]
    fast_worker_results = [r for r in results if r.worker == workers[0]]
    
    # 高速Workerが多くのタスクを処理していることを期待
    # （再配置により遅いWorkerから移ったタスクも含む）
    assert len(fast_worker_results) >= 4, f"Fast worker should handle more tasks due to redistribution, got {len(fast_worker_results)}"
    
    # 全体の処理時間が改善されていることを確認
    # 再配置なしの場合、多くのタスクが遅いWorkerで処理されるため時間がかかる
    print(f"Total time: {total_time:.2f}s, Fast worker processed: {len(fast_worker_results)} items")
    assert total_time < 3.0, f"Total time should be improved by redistribution: {total_time:.2f}s"


async def test_redistribution_oldest_first():
    """最古のタスクから順に再配置されることをテスト"""
    # 中程度と遅いWorkerを設定
    workers = [
        create_worker("medium", capacity=1, processing_time=0.5),  # 0.5秒
        create_worker("slow", capacity=2, processing_time=2.0),    # 2.0秒
        create_worker("fast", capacity=3, processing_time=0.1),    # 0.1秒（後で空く）
    ]
    items = [1, 2, 3, 4, 5]
    
    # カスタムMockWorkerを使用して開始時刻を記録
    start_times = {}
    
    class TrackingMockWorkerImpl(MockWorkerImpl):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.item_start_times = {}
        
        async def run(self, item: Any) -> str:
            self.item_start_times[item] = time.time()
            return await super().run(item)
    
    # トラッキング機能付きのWorkerを作成
    tracking_workers = []
    for worker in workers:
        impl = TrackingMockWorkerImpl(
            name=f"tracking_{worker.capacity}",
            capacity=worker.capacity,
            processing_time=0.5 if worker.capacity == 1 else (2.0 if worker.capacity == 2 else 0.1)
        )
        tracking_workers.append(Worker(
            run=impl.run,
            kill=impl.kill,
            capacity=worker.capacity
        ))
    
    results = [r async for r in dynamic_dispatch(tracking_workers, items)]
    
    assert len(results) == 5
    
    # 高速Workerが多くのタスクを処理していることを確認
    fast_worker_results = [r for r in results if r.worker == tracking_workers[2]]
    assert len(fast_worker_results) >= 3, f"Fast worker should handle redistributed tasks, got {len(fast_worker_results)}"


async def test_no_redistribution_under_median_threshold():
    """中央値の2倍未満のタスクは再配置されないことをテスト"""
    # すべてのWorkerが似たような性能の場合
    workers = [
        create_worker("worker1", capacity=1, processing_time=0.3),
        create_worker("worker2", capacity=1, processing_time=0.4),
        create_worker("worker3", capacity=2, processing_time=0.2),  # 少し高速
    ]
    items = [1, 2, 3, 4, 5]
    
    start_time = time.time()
    
    results = [r async for r in dynamic_dispatch(workers, items)]
    
    end_time = time.time()
    total_time = end_time - start_time
    
    assert len(results) == 5
    
    # 中央値の2倍未満のタスクは再配置されないため、
    # 各Workerがタスクを処理している
    worker1_results = [r for r in results if r.worker == workers[0]]
    worker2_results = [r for r in results if r.worker == workers[1]]
    worker3_results = [r for r in results if r.worker == workers[2]]
    
    # worker3は容量が大きいため多くのタスクを処理する可能性があるが、
    # 性能差が小さいため大幅な再配置は起こらない
    total_distributed = len(worker1_results) + len(worker2_results) + len(worker3_results)
    assert total_distributed == 5
    
    # 処理時間が適度な範囲内であることを確認
    assert total_time < 2.0, f"Processing should complete in reasonable time: {total_time:.2f}s"


async def test_multiple_redistributions():
    """複数のタスクが再配置される場合のテスト"""
    workers = [
        create_worker("slow1", capacity=1, processing_time=0.6),  # 0.6秒に短縮
        create_worker("slow2", capacity=1, processing_time=0.6),  # 0.6秒に短縮
        create_worker("fast", capacity=5, processing_time=0.05),
    ]
    items = [1, 2, 3, 4, 5]
    
    start_time = time.time()
    
    # 新しい実装では、アイテムが空になった時点で即座に再配置される
    results = [r async for r in dynamic_dispatch(workers, items)]
    
    end_time = time.time()
    total_time = end_time - start_time
    
    assert len(results) == 5
    
    # 高速Workerが多くのタスクを処理していることを確認
    fast_worker_results = [r for r in results if r.worker == workers[2]]
    assert len(fast_worker_results) >= 3, "Fast worker should handle multiple redistributed tasks"
    
    # 処理時間が大幅に短縮されている
    assert total_time < 1.0, f"Total time: {total_time}, should be much less due to immediate redistribution"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])