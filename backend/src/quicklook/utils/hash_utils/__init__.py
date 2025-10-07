from __future__ import annotations

import hashlib
import json
from typing import Any, Iterable

__all__ = ['hash_iterable']


def hash_iterable(values: Iterable[int]) -> int:
    """Calculate a deterministic hash value for an iterable of integers.

    The result is stable across Python processes and interpreter versions.
    It uses BLAKE2b with an 64-bit digest to produce a non-negative integer.
    """
    hasher = hashlib.blake2b(digest_size=8)

    for value in values:
        value_bytes = _int_to_bytes(value)
        length_prefix = len(value_bytes).to_bytes(4, byteorder='big', signed=False)
        hasher.update(length_prefix)
        hasher.update(value_bytes)

    return int.from_bytes(hasher.digest(), byteorder='big', signed=False)


def _int_to_bytes(value: int) -> bytes:
    if value == 0:
        return b"\x00"

    length = (value.bit_length() + 7) // 8 or 1
    # Ensure signed representation fits.
    while True:
        try:
            return value.to_bytes(length, byteorder='big', signed=True)
        except OverflowError:
            length += 1


def json_digest(obj: Any):
    s = json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.blake2b(s.encode("utf-8"), digest_size=16).digest()
