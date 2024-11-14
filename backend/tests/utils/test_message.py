import asyncio
import io
import pytest
from quicklook.utils.message import encode_message, decode_message, message_from_stream, message_from_async_stream

def test_encode_decode_message():
    msg = {"key": "value"}
    encoded = encode_message(msg)
    decoded = decode_message(encoded)
    assert decoded == msg

def test_message_from_stream():
    msg = {"key": "value"}
    encoded = encode_message(msg)
    stream = io.BytesIO(encoded)
    decoded = message_from_stream(stream)
    assert decoded == msg

@pytest.mark.asyncio
async def test_message_from_async_stream():
    msg = {"key": "value"}
    encoded = encode_message(msg)
    stream = asyncio.StreamReader()
    stream.feed_data(encoded)
    stream.feed_eof()
    decoded = await message_from_async_stream(stream)
    assert decoded == msg

def test_message_from_stream_eof_error():
    stream = io.BytesIO(b'')
    with pytest.raises(EOFError):
        message_from_stream(stream)