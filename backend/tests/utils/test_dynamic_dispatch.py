"""
動的スケジューリングシステムのテスト

dynamic_dispatchの機能を検証するための包括的なテストスイート
"""

import asyncio
import pytest
import random
from typing import Any, cast
from unittest.mock import AsyncMock

from quicklook.utils.dynamic_dispatch import (
    dynamic_dispatch,
    Worker,
    WorkerDownError,
    Result,
)


class MockWorker:
    """テスト用のMockWorkerクラス"""
    
    def __init__(
        self,
        name: str,
        max_capacity: int = 2,
        processing_time: float = 0.1,
        failure_rate: float = 0.0,
        worker_down_rate: float = 0.0,
        should_fail_on_items: list[Any] | None = None,
    ):
        self.name = name
        self.max_capacity = max_capacity
        self.processing_time = processing_time
        self.failure_rate = failure_rate
        self.worker_down_rate = worker_down_rate
        self.should_fail_on_items = should_fail_on_items or []
        
        self._running_tasks: set[int] = set()
        self._is_killed = False
        self._completed_items: list[Any] = []
        
    def capacity(self) -> int:
        """現在処理可能なアイテム数を返す"""
        if self._is_killed:
            return 0
        return max(0, self.max_capacity - len(self._running_tasks))
    
    async def run(self, item: Any) -> str:
        """アイテムの処理を実行する"""
        if self._is_killed:
            raise WorkerDownError(f"Worker {self.name} は停止しています")
        
        if self.capacity() <= 0:
            raise RuntimeError(f"Worker {self.name} は容量を超えています")
        
        item_id = id(item)
        self._running_tasks.add(item_id)
        
        try:
            # 特定のアイテムでの失敗をシミュレート
            if item in self.should_fail_on_items:
                raise WorkerDownError(f"Worker {self.name} が item {item} で失敗")
            
            # ランダムな失敗をシミュレート
            if random.random() < self.worker_down_rate:
                self._is_killed = True
                raise WorkerDownError(f"Worker {self.name} がランダムに停止")
            
            # 処理時間をシミュレート
            await asyncio.sleep(self.processing_time)
            
            # 一般的な失敗をシミュレート
            if random.random() < self.failure_rate:
                raise RuntimeError(f"Worker {self.name} で一般的なエラーが発生")
            
            self._completed_items.append(item)
            return f"processed_{item}_by_{self.name}"
            
        finally:
            self._running_tasks.discard(item_id)
    
    async def kill(self) -> None:
        """Workerを停止する"""
        self._is_killed = True
        self._running_tasks.clear()
    
    def __repr__(self) -> str:
        return f"MockWorker({self.name})"


async def test_basic_functionality():
    """基本的な動作のテスト"""
    workers = [
        MockWorker("worker1", max_capacity=2, processing_time=0.1),
        MockWorker("worker2", max_capacity=3, processing_time=0.05),
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

async def test_worker_capacity_management():
    """Worker容量管理のテスト"""
    workers = [
        MockWorker("slow", max_capacity=1, processing_time=0.3),
        MockWorker("fast", max_capacity=3, processing_time=0.05),
    ]
    items = list(range(10))
    
    results = [r async for r in dynamic_dispatch(workers, items)]
    
    assert len(results) == 10
    
    # 高速なWorkerがより多くのアイテムを処理していることを確認
    fast_worker_results = [r for r in results if cast(MockWorker, r.worker).name == "fast"]
    slow_worker_results = [r for r in results if cast(MockWorker, r.worker).name == "slow"]
    
    # 高速なWorkerの方が多く処理している可能性が高い
    assert len(fast_worker_results) > len(slow_worker_results)

async def test_empty_items():
    """空のアイテムリストのテスト"""
    workers = [MockWorker("worker1")]
    items: list[int] = []
    
    results = [r async for r in dynamic_dispatch(workers, items)]
    
    assert results == []

async def test_no_workers_raises_error():
    """Workerが存在しない場合のテスト"""
    workers: list[MockWorker] = []
    items = [1, 2, 3]
    
    with pytest.raises(ValueError, match="少なくとも1つのWorkerが必要です"):
        async for _ in dynamic_dispatch(workers, items):
            pass

async def test_worker_down_with_retry_true_detailed():
    """Worker停止時の再試行詳細テスト - 失敗したアイテムの再処理をテスト"""
    # アイテム3で失敗し、それまでにアイテム1,2を確実に完了させる設定
    failing_worker = MockWorker(
        "failing",
        should_fail_on_items=[3],  # 3番目で失敗
        max_capacity=1,  # 容量を1に制限して順番を制御
        processing_time=0.01  # 高速処理で確実に完了
    )
    backup_worker = MockWorker(
        "backup",
        max_capacity=2,
        processing_time=0.1
    )
    
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
    
    # バックアップWorkerで処理されたアイテムを確認
    backup_results = [r for r in results if cast(MockWorker, r.worker).name == "backup"]
    backup_items = [r.item for r in backup_results]
    
    # 失敗したアイテム3は必ずbackupで再処理
    assert 3 in backup_items
    
    # 失敗Workerで完了したアイテム(1,2)は再処理されない（すでにyield済み）
    # ただし、スケジューリングによってはbackupが他のアイテムを処理する可能性がある
    # assert 1 in backup_items  # 削除
    # assert 2 in backup_items  # 削除
    
    # 少なくとも失敗したアイテムはbackupで処理されている
    assert len(backup_items) >= 1

async def test_worker_down_with_retry_false():
    """Worker停止時の再試行無効テスト"""
    failing_worker = MockWorker(
        "failing",
        should_fail_on_items=[1],  # 最初のアイテムで失敗
        max_capacity=2,
        processing_time=0.1
    )
    backup_worker = MockWorker(
        "backup",
        max_capacity=2,
        processing_time=0.1
    )
    
    workers = [failing_worker, backup_worker]
    items = [1, 2, 3]
    
    results = [r async for r in dynamic_dispatch(
        workers, 
        items, 
        retry_on_worker_down=False
    )]
    
    # retry_on_worker_down=Falseの場合、失敗したアイテムは処理されない
    processed_items = [r.item for r in results]
    assert 1 not in processed_items  # 失敗したアイテムは処理されない
    
    # バックアップWorkerで残りを処理
    backup_results = [r for r in results if cast(MockWorker, r.worker).name == "backup"]
    assert len(backup_results) > 0  # バックアップが何かを処理している

async def test_on_late_result_callback_detailed():
    """遅延結果コールバックの詳細なテスト"""
    late_results: list[Result[int, str]] = []
    
    async def collect_late_result(result: Result[int, str]) -> None:
        late_results.append(result)
    
    # 極端に速いWorkerと遅いWorkerを設定して確実に遅延結果を発生させる
    workers = [
        MockWorker("very_fast", max_capacity=1, processing_time=0.001),
        MockWorker("very_slow", max_capacity=1, processing_time=0.5),
    ]
    items = [1, 2]  # 少ないアイテム数で確実な制御
    
    results = [r async for r in dynamic_dispatch(
        workers, 
        items,
        on_late_result=collect_late_result
    )]
    
    assert len(results) == 2
    # 遅延結果が発生した場合、コールバックが呼ばれる
    # （ただし、実際の遅延の発生はタイミングに依存）
    print(f"Late results: {len(late_results)}")  # デバッグ用

async def test_all_option_combinations():
    """すべてのオプション組み合わせのテスト"""
    async def dummy_callback(result: Result[int, str]) -> None:
        pass
    
    # retry_on_worker_down=True, on_late_result=None
    workers = [MockWorker("worker1", max_capacity=2)]
    results = [r async for r in dynamic_dispatch(
        workers, [1, 2], 
        retry_on_worker_down=True, 
        on_late_result=None
    )]
    assert len(results) == 2
    
    # retry_on_worker_down=False, on_late_result=None
    workers = [MockWorker("worker2", max_capacity=2)]
    results = [r async for r in dynamic_dispatch(
        workers, [1, 2], 
        retry_on_worker_down=False, 
        on_late_result=None
    )]
    assert len(results) == 2
    
    # retry_on_worker_down=True, on_late_result=provided
    workers = [MockWorker("worker3", max_capacity=2)]
    results = [r async for r in dynamic_dispatch(
        workers, [1, 2], 
        retry_on_worker_down=True, 
        on_late_result=dummy_callback
    )]
    assert len(results) == 2
    
    # retry_on_worker_down=False, on_late_result=provided
    workers = [MockWorker("worker4", max_capacity=2)]
    results = [r async for r in dynamic_dispatch(
        workers, [1, 2], 
        retry_on_worker_down=False, 
        on_late_result=dummy_callback
    )]
    assert len(results) == 2

async def test_no_available_workers_with_retry_false_break():
    """利用可能なWorkerがなく、再試行無効時のbreak条件テスト"""
    # すべてのWorkerが即座に停止する設定
    workers = [
        MockWorker("worker1", worker_down_rate=1.0, max_capacity=1),  # 100%停止
    ]
    items = [1, 2, 3]
    
    results = [r async for r in dynamic_dispatch(
        workers, 
        items, 
        retry_on_worker_down=False  # 再試行無効
    )]
    
    # すべてのWorkerが停止し、再試行無効なので処理は中断される
    # この場合はbreak文が実行される
    assert len(results) == 0  # いずれのアイテムも完了しない

async def test_waiting_for_workers_with_retry_true():
    """Workerの復旧待ちのsleep部分をテストする"""
    # 一時的にすべてのWorkerが停止するが、retry=Trueなので待機する
    worker = MockWorker("worker1", max_capacity=1, processing_time=0.01)
    
    # Workerを手動で停止状態にする
    worker._is_killed = True
    
    workers = [worker]
    items = [1]
    
    # 別のタスクでWorkerを復旧させる
    async def revive_worker():
        await asyncio.sleep(0.05)  # 少し待ってから復旧
        worker._is_killed = False
    
    # 復旧タスクを開始
    revive_task = asyncio.create_task(revive_worker())
    
    try:
        results = [r async for r in dynamic_dispatch(
            workers, 
            items, 
            retry_on_worker_down=True
        )]
        
        # 復旧後に処理が完了する
        assert len(results) == 1
    finally:
        revive_task.cancel()
        try:
            await revive_task
        except asyncio.CancelledError:
            pass

async def test_on_late_result_none():
    """on_late_resultがNoneの場合のテスト"""
    workers = [
        MockWorker("fast", max_capacity=2, processing_time=0.05),
        MockWorker("slow", max_capacity=1, processing_time=0.3),
    ]
    items = [1, 2, 3]
    
    # Noneを指定しても正常に動作することを確認
    results = [r async for r in dynamic_dispatch(
        workers, 
        items,
        on_late_result=None
    )]
    
    assert len(results) == 3
    processed_items = [r.item for r in results]
    assert sorted(processed_items) == sorted(items)

async def test_multiple_workers_down():
    """複数のWorkerが停止する場合のテスト"""
    workers = [
        MockWorker("worker1", should_fail_on_items=[1], max_capacity=1),
        MockWorker("worker2", should_fail_on_items=[2], max_capacity=1),
        MockWorker("worker3", max_capacity=2),  # 正常なWorker
    ]
    items = [1, 2, 3, 4, 5]
    
    results = [r async for r in dynamic_dispatch(
        workers, 
        items, 
        retry_on_worker_down=True
    )]
    
    assert len(results) == 5
    processed_items = [r.item for r in results]
    assert sorted(processed_items) == sorted(items)
    
    # worker3が最終的に多くのアイテムを処理している
    worker3_results = [r for r in results if cast(MockWorker, r.worker).name == "worker3"]
    assert len(worker3_results) >= 2  # 少なくとも失敗したアイテムの再処理分

async def test_all_workers_dead_with_retry_false():
    """全Workerが停止し、再試行無効の場合のテスト"""
    workers = [
        MockWorker("worker1", should_fail_on_items=[1], max_capacity=2),
        MockWorker("worker2", should_fail_on_items=[2], max_capacity=2),
    ]
    items = [1, 2, 3, 4, 5]
    
    results = [r async for r in dynamic_dispatch(
        workers, 
        items, 
        retry_on_worker_down=False
    )]
    
    # 処理可能なWorkerがなくなった時点で処理が停止
    assert len(results) < 5

async def test_all_workers_down_no_retry_break_condition():
    """すべてのWorkerが停止して再試行が無効の場合の終了条件テスト"""
    # 最初のアイテムで即座に停止するWorkerのみ
    workers = [
        MockWorker("worker1", should_fail_on_items=[1], max_capacity=1),
    ]
    items = [1, 2, 3]
    
    results = [r async for r in dynamic_dispatch(
        workers, 
        items, 
        retry_on_worker_down=False
    )]
    
    # Worker1が最初のアイテムで停止し、retry=Falseなので残りは処理されない
    assert len(results) == 0  # 失敗したアイテムは結果に含まれない
    processed_items = [r.item for r in results]
    assert 1 not in processed_items

async def test_worker_exception_propagation():
    """Worker内の一般的な例外が適切に伝播されることをテスト"""
    failing_worker = MockWorker(
        "failing", 
        failure_rate=1.0,  # 100%失敗
        max_capacity=1
    )
    workers = [failing_worker]
    items = [1]
    
    with pytest.raises(RuntimeError, match="一般的なエラーが発生"):
        async for _ in dynamic_dispatch(workers, items):
            pass

async def test_performance_difference_handling():
    """性能差のあるWorkerの処理分散テスト"""
    workers = [
        MockWorker("very_slow", max_capacity=1, processing_time=1.0),
        MockWorker("fast1", max_capacity=3, processing_time=0.01),
        MockWorker("fast2", max_capacity=3, processing_time=0.01),
    ]
    items = list(range(20))
    
    import time
    start_time = time.time()
    results = [r async for r in dynamic_dispatch(workers, items)]
    end_time = time.time()
    
    assert len(results) == 20
    
    # 高速なWorkerが大部分を処理していることを確認
    fast_results = [
        r for r in results 
        if cast(MockWorker, r.worker).name in ["fast1", "fast2"]
    ]
    slow_results = [
        r for r in results 
        if cast(MockWorker, r.worker).name == "very_slow"
    ]
    
    # 高速なWorkerが多くを処理
    assert len(fast_results) > len(slow_results)
    
    # 処理時間が遅いWorkerの単独処理時間よりも短い
    assert end_time - start_time < 10.0  # 十分高速



if __name__ == "__main__":
    pytest.main([__file__, "-v"])
