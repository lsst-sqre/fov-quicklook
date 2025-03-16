from collections import OrderedDict
from typing import TypeVar, Generic

T = TypeVar('T')

class SizeLimitedSet(Generic[T]):
    def __init__(self, max_size: int):
        self.max_size: int = max_size
        self._data: OrderedDict[T, None] = OrderedDict()

    def add(self, item: T) -> None:
        # アイテムが既に存在する場合は削除して再追加
        if item in self._data:
            del self._data[item]
        # サイズが上限に達している場合は最初のアイテムを削除
        elif len(self._data) >= self.max_size:
            self._data.popitem(last=False)
        self._data[item] = None

    def __contains__(self, item: T) -> bool:
        return item in self._data

    def __len__(self) -> int:
        return len(self._data)

    def __iter__(self):
        return iter(self._data)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({list(self._data.keys())})"
