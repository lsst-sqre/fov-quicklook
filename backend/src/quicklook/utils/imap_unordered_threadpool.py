from __future__ import annotations

from collections.abc import Iterable, Iterator
from concurrent.futures import FIRST_COMPLETED, Future, ThreadPoolExecutor, wait
from typing import Callable, Optional, ParamSpec, TypeVar

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

    # 先行投入（初回は同期的に取得。パイプライン開始前なのでブロックしても問題ない）
    for _ in range(max_in_flight):
        try:
            x = next(it)
        except StopIteration:
            break
        in_flight.add(executor.submit(func, x))

    # refill を別スレッドで行うための executor（1スレッド）
    # メインの executor は download 用なので、refill で占有しないよう分離する。
    with ThreadPoolExecutor(1, thread_name_prefix="refill") as refill_executor:
        input_exhausted = False
        refill_future: Future | None = None

        while in_flight or refill_future is not None:
            wait_set: set[Future] = set(in_flight)
            if refill_future is not None:
                wait_set.add(refill_future)

            done, remaining = wait(wait_set, return_when=FIRST_COMPLETED)

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

            # in_flight が max_in_flight 未満なら refill を開始
            if not input_exhausted and refill_future is None and len(in_flight) < max_in_flight:
                refill_future = refill_executor.submit(_try_next, it)
