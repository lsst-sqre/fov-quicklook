"""`quicklook.utils.rtree`のユニットテスト."""

from __future__ import annotations

import random
from typing import Sequence

import pytest

from quicklook.utils.geom import BBox
from quicklook.utils.rtree import RectangleIndex


def _intersects(a: Sequence[float], b: Sequence[float]) -> bool:
    aminx, aminy, amaxx, amaxy = a
    bminx, bminy, bmaxx, bmaxy = b
    return not (
        amaxx < bminx or aminx > bmaxx or amaxy < bminy or aminy > bmaxy
    )


def test_basic_intersection() -> None:
    index = RectangleIndex(max_leaf_size=2)
    index.insert(0, (0.0, 0.0, 10.0, 10.0))
    index.insert(1, (5.0, 5.0, 15.0, 15.0))
    index.insert(2, (20.0, 20.0, 30.0, 30.0))

    result = sorted(index.intersection((4.0, 4.0, 12.0, 12.0)))
    assert result == [0, 1]


def test_no_overlap_returns_empty() -> None:
    index = RectangleIndex()
    index.insert(0, (0.0, 0.0, 10.0, 10.0))

    assert list(index.intersection((20.0, 20.0, 21.0, 21.0))) == []


def test_accepts_bbox_instances() -> None:
    index = RectangleIndex()
    bbox = BBox(minx=0.0, miny=0.0, maxx=5.0, maxy=5.0)
    index.insert(10, bbox)

    result = list(index.intersection(BBox(minx=2.0, miny=2.0, maxx=3.0, maxy=3.0)))
    assert result == [10]


def test_invalid_bounds_raise_value_error() -> None:
    index = RectangleIndex()

    with pytest.raises(ValueError):
        index.insert(0, (5.0, 0.0, 1.0, 1.0))

    with pytest.raises(ValueError):
        list(index.intersection((0.0, 5.0, 1.0, 1.0)))


def test_tree_rebuild_after_insert() -> None:
    index = RectangleIndex()
    index.insert(0, (0.0, 0.0, 1.0, 1.0))
    first_query = list(index.intersection((0.0, 0.0, 1.0, 1.0)))
    assert first_query == [0]

    index.insert(1, (2.0, 2.0, 4.0, 4.0))
    second_query = list(index.intersection((3.0, 3.0, 3.5, 3.5)))
    assert second_query == [1]


def test_bulk_load_matches_insert() -> None:
    items = [(i, (float(i), float(i), float(i + 1), float(i + 1))) for i in range(5)]
    index = RectangleIndex()
    index.bulk_load(items)

    result = sorted(index.intersection((1.5, 1.5, 3.5, 3.5)))
    assert result == [1, 2, 3]


def test_random_queries_match_naive() -> None:
    rng = random.Random(42)
    num_rects = 128
    rects: list[tuple[float, float, float, float]] = []

    index = RectangleIndex(max_leaf_size=6)

    for i in range(num_rects):
        minx = rng.uniform(0.0, 100.0)
        miny = rng.uniform(0.0, 100.0)
        width = rng.uniform(0.5, 5.0)
        height = rng.uniform(0.5, 5.0)
        bounds = (minx, miny, minx + width, miny + height)
        rects.append(bounds)
        index.insert(i, bounds)

    def naive(query: Sequence[float]) -> list[int]:
        return [i for i, rect in enumerate(rects) if _intersects(rect, query)]

    for _ in range(20):
        qminx = rng.uniform(0.0, 100.0)
        qminy = rng.uniform(0.0, 100.0)
        qwidth = rng.uniform(0.5, 10.0)
        qheight = rng.uniform(0.5, 10.0)
        query = (qminx, qminy, qminx + qwidth, qminy + qheight)

        expected = naive(query)
        result = sorted(index.intersection(query))
        assert result == expected
