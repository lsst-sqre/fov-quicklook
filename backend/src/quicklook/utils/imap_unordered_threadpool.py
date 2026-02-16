from __future__ import annotations

from collections.abc import Iterable, Iterator
from concurrent.futures import FIRST_COMPLETED, Future, ThreadPoolExecutor, wait
from typing import Callable, Optional, ParamSpec, TypeVar

T = TypeVar("T")
R = TypeVar("R")
P = ParamSpec("P")


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

    例外は yield 時の fut.result() で送出されます（multiprocessing.Pool.imap_unordered と同様）。
    """
    it = iter(iterable)

    in_flight: set[Future[R]] = set()

    # 先行投入
    for _ in range(max_in_flight):
        try:
            x = next(it)
        except StopIteration:
            break
        in_flight.add(executor.submit(func, x))

    # 完了分を返しつつ、終わった分だけ補充
    # NOTE: yieldとrefillを分離する。以前は for fut in done ループ内で
    # yield → next(it) を交互に行っていたが、next(it) がブロックすると
    # 他の完了済み future が yield できなくなるバグがあった。
    input_exhausted = False
    while in_flight:
        done, in_flight = wait(in_flight, return_when=FIRST_COMPLETED)
        for fut in done:
            yield fut.result()

        if not input_exhausted:
            for _ in range(len(done)):
                try:
                    x = next(it)
                except StopIteration:
                    input_exhausted = True
                    break
                in_flight.add(executor.submit(func, x))
