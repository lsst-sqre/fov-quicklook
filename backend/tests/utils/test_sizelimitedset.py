import pytest
from quicklook.utils.sizelimitedset import SizeLimitedSet

def test_add_and_contains() -> None:
    s: SizeLimitedSet[int] = SizeLimitedSet(3)
    s.add(1)
    s.add(2)
    s.add(3)
    assert 1 in s
    assert 2 in s
    assert 3 in s

def test_size_limit() -> None:
    s: SizeLimitedSet[int] = SizeLimitedSet(3)
    s.add(1)
    s.add(2)
    s.add(3)
    s.add(4)
    assert 1 not in s
    assert 2 in s
    assert 3 in s
    assert 4 in s

def test_duplicate_add() -> None:
    s: SizeLimitedSet[int] = SizeLimitedSet(3)
    s.add(1)
    s.add(2)
    s.add(2)
    s.add(3)
    assert len(s) == 3
    assert 1 in s
    assert 2 in s
    assert 3 in s

def test_iteration() -> None:
    s: SizeLimitedSet[int] = SizeLimitedSet(3)
    s.add(1)
    s.add(2)
    s.add(3)
    assert list(s) == [1, 2, 3]

def test_repr() -> None:
    s: SizeLimitedSet[int] = SizeLimitedSet(3)
    s.add(1)
    s.add(2)
    s.add(3)
    assert repr(s) == "SizeLimitedSet([1, 2, 3])"
