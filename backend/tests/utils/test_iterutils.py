import asyncio

import pytest

from quicklook.utils.iterutils import async_bytes_iterator_to_stream, asynciter_to_sync, bytes_iterator_to_stream


async def test_asynciter_to_sync_normal():
    async def async_gen():
        for i in range(5):
            await asyncio.sleep(0.01)  # 実際の非同期操作をシミュレート
            yield i

    result = await asynciter_to_sync(async_gen(), list)
    assert result == [0, 1, 2, 3, 4]


async def test_asynciter_to_sync_empty():
    async def async_gen():
        if False:  # 何も生成しない
            yield 0

    result = await asynciter_to_sync(async_gen(), list)
    assert result == []


async def test_asynciter_to_sync_transform():
    async def async_generator():
        for i in range(3):
            yield i

    def transform(items):
        return {i: i * 2 for i in items}

    result = await asynciter_to_sync(async_generator(), transform)
    assert result == {0: 0, 1: 2, 2: 4}


async def test_asynciter_to_sync_exception_in_generator():
    async def failing_generator():
        yield 1
        yield 2
        raise ValueError("Generator error")

    with pytest.raises(ValueError, match="Generator error"):
        await asynciter_to_sync(failing_generator(), list)


async def test_asynciter_to_sync_exception_in_processor():
    async def async_generator():
        for i in range(5):
            yield i

    def failing_processor(items):
        raise RuntimeError("Processor error")

    with pytest.raises(RuntimeError, match="Processor error"):
        await asynciter_to_sync(async_generator(), failing_processor)


def test_single_chunk_read():
    iterator = iter([b'hello world'])
    read = bytes_iterator_to_stream(iterator)

    result = read(11)
    assert result == b'hello world'

    # イテレータが終了したあとの読み込み
    assert read(1) == b''


def test_partial_reads():
    iterator = iter([b'hello world'])
    read = bytes_iterator_to_stream(iterator)

    result1 = read(5)
    assert result1 == b'hello'

    result2 = read(6)
    assert result2 == b' world'

    assert read(1) == b''


def test_multiple_chunks():
    iterator = iter([b'hello', b' ', b'world'])
    read = bytes_iterator_to_stream(iterator)

    result1 = read(6)
    assert result1 == b'hello '

    result2 = read(5)
    assert result2 == b'world'


def test_read_larger_than_buffer():
    iterator = iter([b'hello', b' ', b'world'])
    read = bytes_iterator_to_stream(iterator)

    result = read(20)
    assert result == b'hello world'


def test_empty_iterator():
    iterator = iter([])
    read = bytes_iterator_to_stream(iterator)

    result = read(10)
    assert result == b''


def test_cross_chunk_boundary():
    iterator = iter([b'abc', b'def', b'ghi'])
    read = bytes_iterator_to_stream(iterator)

    # 最初のチャンクとその次の一部を読み込む
    result1 = read(4)
    assert result1 == b'abcd'

    # 残りを読み込む
    result2 = read(5)
    assert result2 == b'efghi'


def test_asynciter_to_sync_exception():
    async def failing_aiter():
        yield 1
        raise ValueError("Test exception")

    def process_iter(iterator):
        return list(iterator)

    with pytest.raises(ValueError, match="Test exception"):
        asyncio.run(asynciter_to_sync(failing_aiter(), process_iter))


async def test_asynciter_to_sync_exception_propagation():
    """
    例外が非同期イテレーターから正しく伝播するかテスト
    特に、producerで例外が発生した場合に処理が中断され、
    例外が適切に再発生するかを確認
    """
    interrupted = False

    async def failing_async_generator():
        await asyncio.sleep(0.01)  # 少し遅延させる
        yield 1
        await asyncio.sleep(0.01)  # 少し遅延させる
        raise ValueError("Expected test exception")
        yield 2  # 到達しない

    def processor(items):
        nonlocal interrupted
        try:
            # イテレーターからすべての要素を取得しようとする
            result = list(items)
            return result
        except ValueError:
            # producerからの例外が伝播した場合に設定
            interrupted = True
            raise

    with pytest.raises(ValueError, match="Expected test exception"):
        await asynciter_to_sync(failing_async_generator(), processor)

    # 例外によって処理が中断されたことを確認
    assert interrupted, "例外がconsumer関数に伝播していません"


def test_bytes_iterator_to_stream_exact_size():
    data = [b"hello", b" ", b"world"]
    read = bytes_iterator_to_stream(data)
    
    assert read(5) == b"hello"
    assert read(1) == b" "
    assert read(5) == b"world"
    assert read(5) == b""  # イテレータが終了した後は空のバイト列を返す


def test_bytes_iterator_to_stream_smaller_chunks():
    data = [b"ab", b"cde", b"fgh"]
    read = bytes_iterator_to_stream(data)
    
    assert read(1) == b"a"
    assert read(2) == b"bc"
    assert read(3) == b"def"
    assert read(2) == b"gh"
    assert read(1) == b""


def test_bytes_iterator_to_stream_larger_request():
    data = [b"hello", b" world"]
    read = bytes_iterator_to_stream(data)
    
    assert read(20) == b"hello world"  # 要求サイズが利用可能なデータより大きい
    assert read(5) == b""  # データがもう存在しない


async def test_async_bytes_iterator_to_stream_read():
    """基本的な読み取り機能のテスト"""
    async def mock_byte_iterator():
        yield b"hello"
        yield b" "
        yield b"world"

    read = async_bytes_iterator_to_stream(mock_byte_iterator())

    # 正確に5バイト読み取れることを確認
    result = await read(5)
    assert result == b"hello"

    # 1バイト読み取れることを確認
    result = await read(1)
    assert result == b" "

    # 残りを読み取れることを確認
    result = await read(5)
    assert result == b"world"

    # イテレータが終了した後も読み取りが機能することを確認
    result = await read(5)
    assert result == b""


async def test_async_bytes_iterator_to_stream_read_partial():
    """部分的な読み取り機能のテスト"""
    async def mock_byte_iterator():
        yield b"hello world"

    read = async_bytes_iterator_to_stream(mock_byte_iterator())

    # 3バイト読み取り
    result = await read(3)
    assert result == b"hel"

    # 次の4バイト読み取り
    result = await read(4)
    assert result == b"lo w"

    # 残りのバイト読み取り
    result = await read(4)
    assert result == b"orld"


async def test_async_bytes_iterator_to_stream_empty():
    """空のイテレータの動作確認"""
    async def empty_iterator():
        if False:  # 何も生成しない
            yield b""

    read = async_bytes_iterator_to_stream(empty_iterator())

    result = await read(5)
    assert result == b""


async def test_async_bytes_iterator_to_stream_read_more_than_available():
    """利用可能なデータ以上の読み取りをテスト"""
    async def mock_byte_iterator():
        yield b"hello"
        yield b" world"

    read = async_bytes_iterator_to_stream(mock_byte_iterator())

    # 利用可能なデータより多くのバイト数を要求
    result = await read(20)
    assert result == b"hello world"

    # それ以上のデータはない
    result = await read(5)
    assert result == b""
