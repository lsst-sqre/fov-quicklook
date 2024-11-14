from collections import OrderedDict
from typing import Callable, Generic, TypeVar

K = TypeVar('K')
V = TypeVar('V')


class LRUDict(Generic[K, V]):
    def __init__(self, capacity: int):
        self._cache = OrderedDict[K, V]()
        self._capacity = capacity

    def get(self, key: K) -> V:
        if key not in self._cache:
            raise KeyError(key)
        self._cache.move_to_end(key)
        return self._cache[key]

    def has(self, key: K) -> bool:
        return key in self._cache

    def set(self, key: K, value: V) -> None:
        if key in self._cache:
            self._cache.move_to_end(key)
        self._cache[key] = value
        if len(self._cache) > self._capacity:
            k, v = self._cache.popitem(last=False)
            # if self._on_evict:
            #     self._on_evict(k, v)

    def __repr__(self) -> str:  # pragma: no cover
        return f'LRUDict({self._cache!r})'
