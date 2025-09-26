import asyncio
import queue
from typing import AsyncIterable, Awaitable, Callable, Iterable, Protocol, TypeVar

T = TypeVar("T")
R = TypeVar("R")


async def asynciter_to_sync(aiter: AsyncIterable[T], f: Callable[[Iterable[T]], R]) -> R:
    """
    非同期イテレーターを同期的なイテレーターに変換して関数fに適用する。

    この関数は非同期イテレーターからのデータを内部キューを通じて同期的に処理可能な
    イテレーターに変換し、指定された関数fに渡して実行する。処理はスレッドプールで
    行われるため、ブロッキング処理が可能となる。

    Args:
        aiter: 変換する非同期イテレーター
        f: 同期イテレーターを引数に取り、結果を返す関数

    Returns:
        関数fの実行結果

    Raises:
        非同期イテレーター内で発生した例外は、この関数からも再度発生する
    """
    q = queue.Queue()
    result = None

    def consumer():
        def g():
            while True:
                item = q.get()
                if item is None:
                    break
                if isinstance(item, Exception):
                    raise item
                yield item

        return f(g())

    async def producer():
        try:
            async for item in aiter:
                q.put(item)
            q.put(None)
        except Exception as e:
            q.put(e)

    producer_task = asyncio.create_task(producer())
    result = await asyncio.to_thread(consumer)
    await producer_task

    return result


def bytes_iterator_to_stream(iterator: Iterable[bytes]) -> Callable[[int], bytes]:
    """
    Iterable[bytes]をread(size: int)で読み出せる関数に変換する

    Args:
        iterator: バイト列のイテレータ

    Returns:
        size バイトを読み込む関数。read.tell()で現在の読み込み位置を取得可能
    """
    it = iter(iterator)
    buffer = bytearray()
    position = 0

    def read(size: int) -> bytes:
        nonlocal buffer, position
        while len(buffer) < size:
            try:
                chunk = next(it)
                buffer.extend(chunk)
            except StopIteration:
                break

        result = bytes(buffer[:size])
        buffer = buffer[size:]
        position += len(result)
        return result

    read.tell = lambda: position  # type: ignore
    return read


def async_bytes_iterator_to_stream(iterator: AsyncIterable[bytes]) -> Callable[[int], Awaitable[bytes]]:
    """
    AsyncIterable[bytes]をasync read(size: int)で読み出せる関数に変換する

    Args:
        iterator: 非同期バイト列のイテレータ

    Returns:
        非同期にsize バイトを読み込む関数
    """
    it = aiter(iterator)
    buffer = bytearray()

    async def read(size: int) -> bytes:
        nonlocal buffer
        while len(buffer) < size:
            try:
                chunk = await anext(it)
                buffer.extend(chunk)
            except StopAsyncIteration:
                break

        result = bytes(buffer[:size])
        buffer = buffer[size:]
        return result

    return read
