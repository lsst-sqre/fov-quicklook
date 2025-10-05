"""
AsyncProcessGenerator - 重い処理を別プロセスで非同期ストリーミング

同期ジェネレーター関数を別プロセスで実行し、そのyieldをasync generatorとして受け取る
ユーティリティです。FastAPIのStreamingResponseなどで利用できます。

プロセスプールを使用して、呼び出しのたびにプロセスを作らずに効率的に実行します。
"""

from typing import ParamSpec
import atexit
import multiprocessing as mp
import traceback
from concurrent.futures import ProcessPoolExecutor
from contextlib import ExitStack, asynccontextmanager
from typing import ContextManager, AsyncGenerator, Callable, Generator, TypeVar

import anyio
import anyio.to_thread

T = TypeVar('T')
P = ParamSpec('P')


class AsyncProcessPool:
    """プロセスプールを使用した非同期ジェネレーター実行

    このクラスはインスタンス変数を持ちません。実際のプロセスプールと
    マネージャは `create_async_process_pool` が作成し、返されるオブジェクト
    に結びつけられます。
    """

    @staticmethod
    async def run_async_process_generator(
        executor: ProcessPoolExecutor,
        manager: object,
        generator_func: Callable[P, Generator[T, None, None]],
        *args: P.args,
        **kwargs: P.kwargs,
    ) -> AsyncGenerator[T, None]:
        """
        同期ジェネレーターを別プロセスで実行し、そのyieldをasync generatorとして受け取る

        Args:
            executor: 既に作成された ProcessPoolExecutor
            manager: multiprocessing.Manager 相互作用用オブジェクト
            generator_func: 実行する同期ジェネレーター関数
            *args, **kwargs: ジェネレーター関数に渡す引数

        Yields:
            ジェネレーター関数がyieldした値

        Raises:
            プロセス内で発生した例外
        """
        if executor is None or manager is None:
            raise RuntimeError("AsyncProcessPool not initialized")

        queue: mp.Queue = manager.Queue()  # type: ignore[attr-defined]

        future = executor.submit(
            _worker_process,
            generator_func,
            queue,
            args,
            kwargs,
        )

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

            await anyio.to_thread.run_sync(future.result)

        except Exception:
            future.cancel()
            raise


_exit_stacks = set()


def _initialize_worker(initializers: list[Callable[[], ContextManager]]) -> None:
    """ワーカープロセスの初期化"""
    stack = ExitStack()
    for init in initializers:
        stack.enter_context(init())

    _exit_stacks.add(stack)

    def exit():
        _exit_stacks.remove(stack)
        stack.close()

    atexit.register(exit)


def _worker_process(
    func: Callable,
    queue: mp.Queue,
    args,
    kwargs,
) -> None:
    """ワーカープロセスでジェネレーターを実行し、結果をQueueに送信"""
    try:
        generator = func(*args, **kwargs)
        for item in generator:
            queue.put(('data', item))
        queue.put(('done', None))
    except Exception as e:
        traceback.print_exc()
        queue.put(('error', e))


@asynccontextmanager
async def create_async_process_pool(
    max_workers: int | None = None,
    initializers: list[Callable[[], ContextManager]] | None = None,
):
    """
    プロセスプールを作成するコンテキストマネージャ

    Args:
        max_workers: プロセスプールのワーカー数（Noneの場合はCPU数）
        initializers: 各ワーカープロセスで実行する初期化関数のリスト

    Yields:
        AsyncProcessPool: プロセスプールインスタンス

    Example:
        >>> async with create_async_process_pool(max_workers=4) as pool:
        ...     async for item in pool.run_async_process_generator(my_generator, 10):
        ...         print(item)
    """
    # create resources locally and expose a small proxy object that
    # provides the same `run_async_process_generator` API expected by callers.
    manager = mp.Manager()
    executor = ProcessPoolExecutor(
        max_workers=max_workers,
        initializer=_initialize_worker,
        initargs=(initializers or [],),
    )

    class _PoolProxy:
        """Minimal proxy exposing the async generator method expected by callers."""

        async def run_async_process_generator(
            self,
            generator_func: Callable[P, Generator[T, None, None]],
            *args: P.args,
            **kwargs: P.kwargs,
        ) -> AsyncGenerator[T, None]:
            async for item in AsyncProcessPool.run_async_process_generator(
                executor, manager, generator_func, *args, **kwargs
            ):
                yield item

    pool = _PoolProxy()

    try:
        yield pool
    finally:
        executor.shutdown(wait=True)
        # type: ignore
        manager.shutdown()
