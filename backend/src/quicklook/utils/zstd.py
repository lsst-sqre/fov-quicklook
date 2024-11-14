import threading
from functools import cache

import zstandard as zstd


def compress(data: bytes) -> bytes:
    return compressor().compress(data)


def compressor():
    return thread_local_compressor(threading.get_ident())


@cache
def thread_local_compressor(thread_id: int):
    return zstd.ZstdCompressor()
