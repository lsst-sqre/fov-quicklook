from collections import OrderedDict
from typing import TypeVar, Generic
import time

T = TypeVar('T')


class SizeLimitedSet(Generic[T]):
    def __init__(self, max_size: int, *, ttl: float | None = None):
        self.max_size: int = max_size
        self.ttl: float | None = ttl
        self._data: OrderedDict[T, float] = OrderedDict()  # アイテム: タイムスタンプ

    def add(self, item: T) -> None:
        current_time = time.time()

        # 期限切れアイテムの削除
        self._cleanup_expired(current_time)

        # アイテムが既に存在する場合は削除して再追加
        if item in self._data:
            del self._data[item]
        # サイズが上限に達している場合は最初のアイテムを削除
        elif len(self._data) >= self.max_size:
            self._data.popitem(last=False)
        self._data[item] = current_time

    def _cleanup_expired(self, current_time: float | None = None) -> None:
        """期限切れのアイテムを削除する"""
        if self.ttl is None:  # TTLが設定されていない場合
            return

        if current_time is None:
            current_time = time.time()

        # 期限切れアイテムを見つけて削除
        expired = [item for item, timestamp in self._data.items() if current_time - timestamp > self.ttl]

        for item in expired:
            del self._data[item]

    def __contains__(self, item: T) -> bool:
        self._cleanup_expired()
        return item in self._data

    def __len__(self) -> int:
        self._cleanup_expired()
        return len(self._data)

    def __iter__(self):
        self._cleanup_expired()
        return iter(self._data)

    def __repr__(self) -> str:
        self._cleanup_expired()
        return f"{self.__class__.__name__}({list(self._data.keys())})"
