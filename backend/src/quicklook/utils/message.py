import asyncio
import pickle
from typing import Any, Awaitable, BinaryIO, Callable


def encode_message(msg: Any) -> bytes:
    payload = pickle.dumps(msg)
    return len(payload).to_bytes(4, 'big') + payload


def decode_message(payload: bytes) -> Any:
    return pickle.loads(payload[4:])


def message_from_stream(stream: BinaryIO) -> Any:
    length_b = stream.read(4)
    if length_b == b'':
        raise EOFError
    length = int.from_bytes(length_b, 'big')
    return pickle.loads(stream.read(length))


async def message_from_async_reader(read: Callable[[int], Awaitable]) -> Any:
    length_b = await read(4)
    if length_b == b'':  # pragma: no cover
        raise EOFError
    length = int.from_bytes(length_b, 'big')
    return pickle.loads(await read(length))


async def message_from_async_stream(stream: asyncio.StreamReader) -> Any:
    return await message_from_async_reader(stream.readexactly)
