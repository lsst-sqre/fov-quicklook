"""
AsyncProcessGenerator - 重い処理を別プロセスで非同期ストリーミング

同期ジェネレーター関数を別プロセスで実行し、そのyieldをasync generatorとして受け取る
ユーティリティ関数です。FastAPIのStreamingResponseなどで利用できます。
"""

import multiprocessing as mp
import traceback
import anyio
import anyio.to_thread
from typing import Callable, AsyncGenerator, TypeVar, Generator

T = TypeVar('T')


async def run_async_process_generator(
    generator_func: Callable[..., Generator[T, None, None]],
    *args,
    **kwargs,
) -> AsyncGenerator[T, None]:
    """
    同期ジェネレーターを別プロセスで実行し、そのyieldをasync generatorとして受け取る

    Args:
        generator_func: 実行する同期ジェネレーター関数
        *args, **kwargs: ジェネレーター関数に渡す引数

    Yields:
        ジェネレーター関数がyieldした値

    Raises:
        プロセス内で発生した例外
    """
    # マルチプロセス用のQueue作成
    queue: mp.Queue = mp.Manager().Queue()  # type: ignore

    # ワーカープロセス開始
    process = mp.Process(target=_worker_process, args=(generator_func, queue, *args), kwargs=kwargs)
    process.start()

    try:
        while True:
            msg_type, data = await anyio.to_thread.run_sync(queue.get)
            if msg_type == 'data':
                yield data
            elif msg_type == 'done':
                break
            elif msg_type == 'error':
                raise data
            else:  # pragma: no cover
                raise RuntimeError(f"Unknown message type: {msg_type}")

    finally:
        # プロセスのクリーンアップ
        if process.is_alive():
            process.terminate()
            process.join(timeout=5)
            if process.is_alive():  # pragma: no cover
                process.kill()
                process.join()


def _worker_process(func: Callable, queue: mp.Queue, *args, **kwargs) -> None:
    """ワーカープロセスでジェネレーターを実行し、結果をQueueに送信"""
    try:
        generator = func(*args, **kwargs)
        for item in generator:
            queue.put(('data', item))
        queue.put(('done', None))
    except Exception as e:  # pragma: no cover
        # 本当はここもテストしているがなぜかcoverageに反映されない
        traceback.print_exc()
        queue.put(('error', e))
