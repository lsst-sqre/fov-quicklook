import threading
import time
from typing import List

import pytest

from quicklook.utils.dynamicsemaphore import DynamicSemaphore


def test_semaphore_acquire_release():
    semaphore = DynamicSemaphore(initial_max_count=2)
    result: List[int] = []
    lock = threading.Lock()

    def worker(thread_id: int) -> None:
        with semaphore:
            with lock:
                result.append(thread_id)
            time.sleep(0.1)

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(4)]
    for t in threads:
        t.start()

    for t in threads:
        t.join()

    assert len(result) == 4  # 全てのスレッドが実行されたことを確認
    assert semaphore.permits_acquired == 0  # 全てのセマフォが解放されていることを確認


def test_semaphore_max_count_change():
    semaphore = DynamicSemaphore(initial_max_count=1)
    result: List[int] = []
    lock = threading.Lock()

    def worker(thread_id: int) -> None:
        with semaphore:
            with lock:
                result.append(thread_id)
            time.sleep(0.1)

    t1 = threading.Thread(target=worker, args=(1,))
    t2 = threading.Thread(target=worker, args=(2,))

    t1.start()
    time.sleep(0.05)  # t1 が先に acquire するように待機
    t2.start()

    time.sleep(0.05)  # t2 が待機状態になる

    semaphore.set_max_count(2)  # セマフォの最大値を変更

    t1.join()
    t2.join()

    assert sorted(result) == [1, 2]  # 両方のスレッドが実行されたことを確認


def test_semaphore_release_without_acquire():
    semaphore = DynamicSemaphore(initial_max_count=1)

    with pytest.raises(ValueError):
        semaphore.release()


def test_semaphore_context_manager_exception():
    semaphore = DynamicSemaphore(initial_max_count=1)

    try:
        with semaphore:
            raise RuntimeError("テスト例外")
    except RuntimeError:
        pass

    assert semaphore.permits_acquired == 0  # 例外が発生してもセマフォが解放されていることを確認


def test_semaphore_waiting_threads():
    semaphore = DynamicSemaphore(initial_max_count=2)
    active_threads: List[int] = []
    lock = threading.Lock()

    def worker(thread_id: int) -> None:
        with semaphore:
            with lock:
                active_threads.append(thread_id)
            time.sleep(0.2)
            with lock:
                active_threads.remove(thread_id)

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(5)]
    for t in threads:
        t.start()

    time.sleep(0.05)

    with lock:
        assert len(active_threads) == 2  # 最初に実行されているスレッドは2つ

    semaphore.set_max_count(4)

    time.sleep(0.05)

    with lock:
        assert len(active_threads) == 4  # セマフォの上限変更後、実行されているスレッドは4つ

    for t in threads:
        t.join()


def test_semaphore_set_max_count_lower():
    semaphore = DynamicSemaphore(initial_max_count=3)
    result: List[int] = []
    lock = threading.Lock()

    def worker(thread_id: int) -> None:
        with semaphore:
            with lock:
                result.append(thread_id)
            time.sleep(0.1)

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(3)]
    for t in threads:
        t.start()

    time.sleep(0.05)
    semaphore.set_max_count(1)  # permits_acquired より小さい値に設定

    for t in threads:
        t.join()

    assert len(result) == 3  # 全てのスレッドが実行されたことを確認
    assert semaphore.max_count == 1  # max_count が更新されていることを確認
