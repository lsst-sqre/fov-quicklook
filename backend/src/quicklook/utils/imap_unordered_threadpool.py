from __future__ import annotations

from collections.abc import Iterable, Iterator
from concurrent.futures import FIRST_COMPLETED, Future, ThreadPoolExecutor, wait
from typing import Callable, ParamSpec, TypeVar

T = TypeVar("T")
R = TypeVar("R")
P = ParamSpec("P")

_EXHAUSTED = object()


def _try_next(it: Iterator[T]) -> T | object:
    """next(it) をStopIteration-safe にラップ。入力枯渇時は _EXHAUSTED を返す。"""
    try:
        return next(it)
    except StopIteration:
        return _EXHAUSTED


def imap_unordered_threadpool(
    executor: ThreadPoolExecutor,
    func: Callable[[T], R],
    iterable: Iterable[T],
    *,
    max_in_flight: int,
) -> Iterator[R]:
    """
    ThreadPoolExecutor で「完了順（unordered）」に結果を逐次取得するヘルパー。
    - func: 単一引数を取り R を返す関数
    - iterable: 入力 T の iterable（巨大/無限でも可）
    - max_in_flight: 同時実行（in-flight）上限。

    next(iterable) がブロックしても completed downloads の yield を妨げない。
    refill は専用スレッドで非同期に行い、refill_future として in_flight と
    一緒に wait() する。

    例外は yield 時の fut.result() で送出されます（multiprocessing.Pool.imap_unordered と同様）。
    """
    it = iter(iterable)

    in_flight: set[Future[R]] = set()

    try:
        first_item = next(it)
    except StopIteration:
        return
    in_flight.add(executor.submit(func, first_item))

    # refill を別スレッドで行うための executor（1スレッド）
    # メインの executor は download 用なので、refill で占有しないよう分離する。
    with ThreadPoolExecutor(1, thread_name_prefix="refill") as refill_executor:
        input_exhausted = False
        refill_future: Future | None = None

        while in_flight or refill_future is not None:
            # 最初の1件完了待ちで詰まらないよう、空きがあれば先に refill を走らせる。
            if not input_exhausted and refill_future is None and len(in_flight) < max_in_flight:
                refill_future = refill_executor.submit(_try_next, it)

            wait_set: set[Future] = set(in_flight)
            if refill_future is not None:
                wait_set.add(refill_future)

            done, _ = wait(wait_set, return_when=FIRST_COMPLETED)

            for fut in done:
                if fut is refill_future:
                    x = fut.result()
                    if x is _EXHAUSTED:
                        input_exhausted = True
                    else:
                        in_flight.add(executor.submit(func, x))
                    refill_future = None
                else:
                    in_flight.discard(fut)
                    yield fut.result()
