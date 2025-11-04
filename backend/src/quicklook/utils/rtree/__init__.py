"""軽量な矩形空間インデックス.

`rtree`のサードパーティ実装が不安定な状況に対応するため、
最小限の機能を提供する軽量な矩形インデックスを実装する。

主な要件:
- 軸に平行な矩形の登録
- 指定された矩形との交差探索

内部的には、矩形群を中心座標で分割しながら
二分木（Bounding Volume Hierarchy）を構築することで高速化している。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Iterator, Sequence

from quicklook.utils.geom import BBox

BoundsLike = Sequence[float] | BBox


@dataclass(slots=True, frozen=True)
class _Rect:
    """軸に平行な矩形."""

    minx: float
    miny: float
    maxx: float
    maxy: float

    @classmethod
    def from_bounds(cls, bounds: BoundsLike) -> "_Rect":
        if isinstance(bounds, BBox):
            minx = float(bounds.minx)
            miny = float(bounds.miny)
            maxx = float(bounds.maxx)
            maxy = float(bounds.maxy)
        else:
            try:
                minx, miny, maxx, maxy = map(float, bounds)  # type: ignore[arg-type]
            except (TypeError, ValueError) as exc:  # pragma: no cover - defensive
                raise TypeError("bounds must be a sequence of four numbers") from exc
        if minx > maxx or miny > maxy:
            msg = f"invalid bounds: min ({minx}, {miny}) exceeds max ({maxx}, {maxy})"
            raise ValueError(msg)
        return cls(minx=minx, miny=miny, maxx=maxx, maxy=maxy)

    def intersects(self, other: "_Rect") -> bool:
        return not (
            self.maxx < other.minx
            or self.minx > other.maxx
            or self.maxy < other.miny
            or self.miny > other.maxy
        )

    def union(self, other: "_Rect") -> "_Rect":
        return _Rect(
            minx=min(self.minx, other.minx),
            miny=min(self.miny, other.miny),
            maxx=max(self.maxx, other.maxx),
            maxy=max(self.maxy, other.maxy),
        )

    def center(self) -> tuple[float, float]:
        return ((self.minx + self.maxx) * 0.5, (self.miny + self.maxy) * 0.5)


@dataclass(slots=True)
class _Node:
    bbox: _Rect
    left: "_Node | None"
    right: "_Node | None"
    items: list[tuple[int, _Rect]] | None

    @property
    def is_leaf(self) -> bool:
        return self.items is not None


class RectangleIndex:
    """矩形交差探索のための軽量インデックス."""

    def __init__(self, max_leaf_size: int = 16) -> None:
        if max_leaf_size <= 0:
            raise ValueError("max_leaf_size must be positive")
        self._max_leaf_size = max_leaf_size
        self._items: list[tuple[int, _Rect]] = []
        self._root: _Node | None = None
        self._dirty = False

    def insert(self, identifier: int, bounds: BoundsLike) -> None:
        rect = _Rect.from_bounds(bounds)
        self._items.append((identifier, rect))
        self._dirty = True

    def bulk_load(self, items: Iterable[tuple[int, BoundsLike]]) -> None:
        for identifier, bounds in items:
            self.insert(identifier, bounds)

    def intersection(self, bounds: BoundsLike) -> Iterator[int]:
        """指定した矩形と重なる識別子を返す."""

        query = _Rect.from_bounds(bounds)
        root = self._ensure_tree()
        if root is None:
            return iter(())

        def _iterator() -> Iterator[int]:
            stack: list[_Node] = [root]
            while stack:
                node = stack.pop()
                if not node.bbox.intersects(query):
                    continue
                if node.is_leaf:
                    assert node.items is not None
                    for identifier, rect in node.items:
                        if rect.intersects(query):
                            yield identifier
                else:
                    if node.left is not None:
                        stack.append(node.left)
                    if node.right is not None:
                        stack.append(node.right)

        return _iterator()

    def __len__(self) -> int:  # pragma: no cover - trivial
        return len(self._items)

    def _ensure_tree(self) -> _Node | None:
        if not self._dirty and self._root is not None:
            return self._root
        if not self._items:
            self._root = None
            self._dirty = False
            return None
        items = list(self._items)
        self._root = _build_bvh(items, self._max_leaf_size)
        self._dirty = False
        return self._root


def _build_bvh(items: list[tuple[int, _Rect]], max_leaf_size: int) -> _Node:
    if len(items) <= max_leaf_size:
        bbox = _combine_bounds(item[1] for item in items)
        return _Node(bbox=bbox, left=None, right=None, items=list(items))

    spread_x = _spread(items, axis=0)
    spread_y = _spread(items, axis=1)
    axis = 0 if spread_x >= spread_y else 1
    items.sort(key=lambda item: item[1].center()[axis])
    mid = len(items) // 2

    left = _build_bvh(items[:mid], max_leaf_size)
    right = _build_bvh(items[mid:], max_leaf_size)
    bbox = left.bbox.union(right.bbox)
    return _Node(bbox=bbox, left=left, right=right, items=None)


def _combine_bounds(rects: Iterable[_Rect]) -> _Rect:
    iterator = iter(rects)
    first = next(iterator)
    minx, miny, maxx, maxy = first.minx, first.miny, first.maxx, first.maxy
    for rect in iterator:
        minx = min(minx, rect.minx)
        miny = min(miny, rect.miny)
        maxx = max(maxx, rect.maxx)
        maxy = max(maxy, rect.maxy)
    return _Rect(minx=minx, miny=miny, maxx=maxx, maxy=maxy)


def _spread(items: list[tuple[int, _Rect]], axis: int) -> float:
    centers = [item[1].center()[axis] for item in items]
    return max(centers) - min(centers)
