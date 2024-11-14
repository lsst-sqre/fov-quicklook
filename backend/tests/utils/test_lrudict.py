import pytest
from quicklook.utils.lrudict import LRUDict


def test_lrudict_put_and_get():
    cache = LRUDict(2)
    cache.set("a", "1")
    assert cache.get("a") == "1"
    cache.set("b", "2")
    assert cache.get("b") == "2"
    assert cache.get("a") == "1"


def test_lrudict_eviction():
    cache = LRUDict(2)
    cache.set("a", "1")
    cache.set("b", "2")
    cache.set("c", "3")
    with pytest.raises(KeyError):
        cache.get("a")
    assert cache.get("b") == "2"
    assert cache.get("c") == "3"


def test_lrudict_update_existing_key():
    cache = LRUDict(2)
    cache.set("a", "1")
    cache.set("a", "2")
    assert cache.get("a") == "2"


def test_lrudict_capacity():
    cache = LRUDict(1)
    cache.set("a", "1")
    cache.set("b", "2")
    with pytest.raises(KeyError):
        cache.get("a")
    assert cache.get("b") == "2"


def test_lrudict_has_key():
    cache = LRUDict(2)
    cache.set("a", "1")
    assert cache.has("a") is True
    assert cache.has("b") is False


def test_lrudict_has_key_after_eviction():
    cache = LRUDict(2)
    cache.set("a", "1")
    cache.set("b", "2")
    cache.set("c", "3")
    assert cache.has("a") is False
    assert cache.has("b") is True
    assert cache.has("c") is True
