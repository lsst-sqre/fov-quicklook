"""
AsyncProcessGeneratorのテストコード
"""

import asyncio
import time
import pytest
from typing import Generator

from quicklook.utils.async_process_generator import run_async_process_generator


def simple_generator(count: int) -> Generator[str, None, None]:
    """テスト用のシンプルなジェネレーター"""
    for i in range(count):
        yield f"item_{i}"


def slow_generator(count: int, delay: float = 0.1) -> Generator[str, None, None]:
    """テスト用の重い処理をシミュレートするジェネレーター"""
    for i in range(count):
        time.sleep(delay)
        yield f"slow_item_{i}"


def generator_with_args(prefix: str, count: int, suffix: str = "") -> Generator[str, None, None]:
    """引数を持つジェネレーター"""
    for i in range(count):
        yield f"{prefix}_{i}{suffix}"


async def test_basic_functionality():
    """基本的な機能のテスト"""
    results = []
    async for item in run_async_process_generator(simple_generator, 3):
        results.append(item)

    assert results == ["item_0", "item_1", "item_2"]


async def test_empty_generator():
    """空のジェネレーターのテスト"""
    results = []
    async for item in run_async_process_generator(simple_generator, 0):
        results.append(item)

    assert results == []


async def test_generator_with_args_and_kwargs():
    """引数とキーワード引数を持つジェネレーターのテスト"""
    results = []
    async for item in run_async_process_generator(generator_with_args, "test", 2, suffix="_end"):
        results.append(item)

    assert results == ["test_0_end", "test_1_end"]


def error_generator() -> Generator[str, None, None]:
    """エラーを発生させるジェネレーター"""
    yield "before_error"
    raise ValueError("Test error")


async def test_error_propagation():
    """エラー伝播のテスト"""
    results = []

    with pytest.raises(ValueError, match="Test error"):
        async for item in run_async_process_generator(error_generator):
            results.append(item)

    # エラー前の値は取得できている
    assert results == ["before_error"]


async def test_slow_generator():
    """重い処理のテスト（時間をかけて確認）"""
    start_time = time.time()
    results = []

    async for item in run_async_process_generator(slow_generator, 3, 0.1):
        results.append(item)
        # 各アイテムがストリーミングされていることを確認
        current_time = time.time()
        elapsed = current_time - start_time
        # 最初のアイテムは比較的早く到着するはず
        if len(results) == 1:
            assert elapsed < 0.5  # 0.5秒以内

    assert results == ["slow_item_0", "slow_item_1", "slow_item_2"]

    # 全体の処理時間も確認（約0.3秒かかるはず）
    total_time = time.time() - start_time
    assert 0.25 < total_time < 0.6  # 多少の余裕を持って


async def test_concurrent_generators():
    """複数の非同期ジェネレーターを同時実行"""

    async def collect_results(gen_func, *args):
        results = []
        async for item in run_async_process_generator(gen_func, *args):
            results.append(item)
        return results

    # 2つの異なるジェネレーターを同時実行
    task1 = asyncio.create_task(collect_results(simple_generator, 2))
    task2 = asyncio.create_task(collect_results(generator_with_args, "concurrent", 2))

    results1, results2 = await asyncio.gather(task1, task2)

    assert results1 == ["item_0", "item_1"]
    assert results2 == ["concurrent_0", "concurrent_1"]


def test_sync_wrapper():
    """同期ラッパーを使ったテスト（asyncio.run使用）"""

    async def async_test():
        results = []
        async for item in run_async_process_generator(simple_generator, 2):
            results.append(item)
        return results

    results = asyncio.run(async_test())
    assert results == ["item_0", "item_1"]


# pytestの非同期テスト実行のため
def test_basic_functionality_sync():
    """基本機能の同期テスト版"""
    asyncio.run(test_basic_functionality())


def test_empty_generator_sync():
    """空ジェネレーターの同期テスト版"""
    asyncio.run(test_empty_generator())


def test_generator_with_args_and_kwargs_sync():
    """引数テストの同期テスト版"""
    asyncio.run(test_generator_with_args_and_kwargs())


def test_error_propagation_sync():
    """エラー伝播の同期テスト版"""
    asyncio.run(test_error_propagation())


def test_slow_generator_sync():
    """重い処理の同期テスト版"""
    asyncio.run(test_slow_generator())


def test_concurrent_generators_sync():
    """並行実行の同期テスト版"""
    asyncio.run(test_concurrent_generators())
