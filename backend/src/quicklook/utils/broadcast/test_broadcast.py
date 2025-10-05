import asyncio
import pytest
from quicklook.utils.broadcast import Broadcast


def test_broadcast_initialization():
    """Broadcastクラスの初期化をテスト"""
    # デフォルト（制限なし）
    broadcast = Broadcast[int]()
    assert broadcast.max_queue_size is None

    # サイズ制限あり
    broadcast_limited = Broadcast[int](max_queue_size=5)
    assert broadcast_limited.max_queue_size == 5


async def test_basic_broadcast():
    """基本的なブロードキャスト機能をテスト"""
    broadcast = Broadcast[int]()
    
    async with broadcast.activate():
        # アイテムを送信
        broadcast.put(1)
        broadcast.put(2)
        
        # 購読して受信
        items = []
        async for item in broadcast.subscribe():
            items.append(item)
            if len(items) >= 2:
                break
        
        assert items == [1, 2]


async def test_queue_size_limit():
    """キューサイズ制限のテスト"""
    broadcast = Broadcast[int](max_queue_size=3)
    
    async with broadcast.activate():
        # まず購読を開始
        subscriber_task = asyncio.create_task(collect_items(broadcast, 3))
        
        # 短時間待機して購読者が準備されるのを待つ
        await asyncio.sleep(0.01)
        
        # 制限を超えてアイテムを送信
        for i in range(5):
            broadcast.put(i)
        
        # 結果を収集
        items = await subscriber_task
        
        # 古いアイテム(0, 1)は削除され、新しいアイテム(2, 3, 4)のみが残る
        assert items == [2, 3, 4]


async def collect_items(broadcast: Broadcast[int], count: int) -> list[int]:
    """指定数のアイテムを収集するヘルパー関数"""
    items = []
    async for item in broadcast.subscribe():
        items.append(item)
        if len(items) >= count:
            break
    return items


async def test_multiple_subscribers_with_limit():
    """複数の購読者がいる場合のキューサイズ制限をテスト"""
    broadcast = Broadcast[str](max_queue_size=2)
    
    async with broadcast.activate():
        # まず2つの購読者を開始
        async def collect_items1():
            items = []
            async for item in broadcast.subscribe():
                items.append(item)
                if len(items) >= 2:
                    break
            return items
        
        async def collect_items2():
            items = []
            async for item in broadcast.subscribe():
                items.append(item)
                if len(items) >= 2:
                    break
            return items
        
        # 購読者タスクを並行開始
        task1 = asyncio.create_task(collect_items1())
        task2 = asyncio.create_task(collect_items2())
        
        # 短時間待機して購読者が準備されるのを待つ
        await asyncio.sleep(0.01)
        
        # 制限を超えてアイテムを送信
        broadcast.put("a")
        broadcast.put("b")
        broadcast.put("c")  # "a"が削除されるはず
        
        # 結果を収集
        items1, items2 = await asyncio.gather(task1, task2)
        
        # 両方の購読者が同じアイテムを受信
        assert items1 == ["b", "c"]
        assert items2 == ["b", "c"]


async def test_no_limit_behavior():
    """制限なしの場合の動作をテスト"""
    broadcast = Broadcast[int]()  # max_queue_size=None
    
    async with broadcast.activate():
        # まず購読を開始
        subscriber_task = asyncio.create_task(collect_items(broadcast, 10))
        
        # 短時間待機して購読者が準備されるのを待つ
        await asyncio.sleep(0.01)
        
        # 多数のアイテムを送信
        for i in range(10):
            broadcast.put(i)
        
        # 結果を収集
        items = await subscriber_task
        
        # すべてのアイテムが保持されている
        assert items == list(range(10))


async def test_queue_overflow_edge_cases():
    """キューオーバーフローのエッジケースをテスト"""
    broadcast = Broadcast[int](max_queue_size=1)
    
    async with broadcast.activate():
        # まず購読を開始
        subscriber_task = asyncio.create_task(collect_items(broadcast, 1))
        
        # 短時間待機して購読者が準備されるのを待つ
        await asyncio.sleep(0.01)
        
        # 1つだけのサイズ制限
        broadcast.put(1)
        broadcast.put(2)  # 1が削除される
        broadcast.put(3)  # 2が削除される
        
        # 結果を収集
        items = await subscriber_task
        
        assert items == [3]