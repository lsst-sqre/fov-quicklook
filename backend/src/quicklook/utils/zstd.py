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


def decompress(data: bytes) -> bytes:
    return decompressor().decompress(data)


def decompressor():
    return thread_local_decompressor(threading.get_ident())


@cache
def thread_local_decompressor(thread_id: int):
    return zstd.ZstdDecompressor()
