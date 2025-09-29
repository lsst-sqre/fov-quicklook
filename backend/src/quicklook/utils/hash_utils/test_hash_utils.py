from quicklook.types import TilePos
from quicklook.utils.hash_utils import hash_iterable


def test_hash_iterable_is_deterministic():
    values = [1, -2, 3, 1000, 2**40]

    first = hash_iterable(values)
    second = hash_iterable(values)

    assert first == second


def test_hash_iterable_distinguishes_sequences():
    values_a = [1, 2, 3]
    values_b = [1, 3, 2]

    assert hash_iterable(values_a) != hash_iterable(values_b)
