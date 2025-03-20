import asyncio
import pytest
from quicklook.utils.orderedsemaphore import OrderedSemaphore


@pytest.mark.asyncio
async def test_semaphore_init():
    """初期化パラメータのテスト"""
    # 正常なケース
    sem = OrderedSemaphore(2)
    assert not sem.locked()

    # 初期値0でも正常
    sem = OrderedSemaphore(0)
    assert sem.locked()

    # 負の値はエラー
    with pytest.raises(ValueError):
        OrderedSemaphore(-1)


@pytest.mark.asyncio
async def test_acquire_release():
    """基本的なacquire/releaseのテスト"""
    sem = OrderedSemaphore(1)

    # 初期状態
    assert not sem.locked()

    # acquire後
    await sem.acquire()
    assert sem.locked()

    # release後
    sem.release()
    assert not sem.locked()


@pytest.mark.asyncio
async def test_context_manager():
    """コンテキストマネージャーの動作確認"""
    sem = OrderedSemaphore(1)

    assert not sem.locked()
    async with sem:
        assert sem.locked()
    assert not sem.locked()


@pytest.mark.asyncio
async def test_multiple_acquires():
    """複数のacquireを行った場合のテスト"""
    sem = OrderedSemaphore(2)

    await sem.acquire()
    assert not sem.locked()

    await sem.acquire()
    assert sem.locked()


@pytest.mark.asyncio
async def test_ordered_acquisition():
    """順序付き獲得のテスト - これがOrderedSemaphoreの核心部分"""
    sem = OrderedSemaphore(1)
    execution_order: list[int] = []

    async def worker(id: int) -> None:
        await sem.acquire()
        execution_order.append(id)
        await asyncio.sleep(0.01)  # 実行順序に差をつけるための短い遅延
        sem.release()

    # 複数のタスクを作成
    tasks = [asyncio.create_task(worker(i)) for i in range(5)]

    # 全てのタスクが完了するのを待つ
    await asyncio.gather(*tasks)

    # 実行順序が要求順（0,1,2,3,4）と同じになっていることを確認
    assert execution_order == [0, 1, 2, 3, 4]


@pytest.mark.asyncio
async def test_exception_during_acquire():
    """acquire中に例外が発生した場合のテスト"""
    sem = OrderedSemaphore(1)
    await sem.acquire()  # セマフォをロック

    # 例外を発生させるタスク
    async def failing_task() -> None:
        try:
            # このacquireは待機状態になる
            await asyncio.wait_for(sem.acquire(), 0.1)
        except asyncio.TimeoutError:
            pass  # タイムアウトは期待通り

    await failing_task()

    # 内部状態が正常であることを確認
    sem.release()
    assert not sem.locked()

    # 再度正常にacquire/releaseできることを確認
    await sem.acquire()
    assert sem.locked()
    sem.release()
    assert not sem.locked()


@pytest.mark.asyncio
async def test_concurrency_limit():
    """同時実行数の上限テスト"""
    # 同時実行数の上限を3に設定
    sem = OrderedSemaphore(3)
    running_tasks: list[int] = []
    max_concurrent = 0
    event = asyncio.Event()

    async def worker(worker_id: int) -> None:
        await sem.acquire()
        try:
            # 実行中のタスクとして記録
            running_tasks.append(worker_id)
            # 現在の同時実行数を記録
            nonlocal max_concurrent
            max_concurrent = max(max_concurrent, len(running_tasks))
            # イベントが設定されるまで待機（全タスクが開始できるようにする）
            await event.wait()
        finally:
            running_tasks.remove(worker_id)
            sem.release()

    # 5つのタスクを開始（上限3のため、最初の3つだけが即時実行されるはず）
    tasks = [asyncio.create_task(worker(i)) for i in range(5)]

    # タスクが開始できるよう少し待機
    await asyncio.sleep(0.1)

    # 現時点で3つのタスクだけが実行中であることを確認
    assert len(running_tasks) == 3

    # イベントを設定して、すべてのタスクが完了するよう指示
    event.set()

    # すべてのタスクが完了するのを待つ
    await asyncio.gather(*tasks)

    # 最大同時実行数が設定した上限と一致することを確認
    assert max_concurrent == 3
    # 全てのタスクが完了したことを確認
    assert len(running_tasks) == 0


@pytest.mark.asyncio
async def test_sequential_execution_with_limit():
    """上限付きセマフォでの順次実行テスト"""
    sem = OrderedSemaphore(2)
    result: list[int] = []

    async def worker(worker_id: int) -> None:
        await sem.acquire()
        try:
            # 短い遅延を入れて実行タイミングに差をつける
            await asyncio.sleep(0.01 * worker_id)
            result.append(worker_id)
        finally:
            sem.release()

    # タスクを逆順で作成（実行順序が作成順と異なることを確認するため）
    tasks = [asyncio.create_task(worker(i)) for i in range(5, 0, -1)]

    # 全タスクが完了するのを待つ
    await asyncio.gather(*tasks)

    # セマフォの同時実行制限により、5, 4が先に実行され、
    # その後3, 2, 1の順で処理されるはず
    # 各タスク内の遅延が実行順序に影響するため、結果は作成順と異なる
    assert len(result) == 5
    # すべてのワーカーIDが結果に含まれることを確認
    assert set(result) == {1, 2, 3, 4, 5}
