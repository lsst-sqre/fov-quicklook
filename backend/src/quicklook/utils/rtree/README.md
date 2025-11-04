# quicklook.utils.rtree

## Background
The existing third-party `rtree` implementation showed unstable behavior in some cases,
so we implemented a custom module providing equivalent search functionality with minimal dependencies.
This module is located in `src/quicklook/utils/rtree/__init__.py` and provides fast intersection searches
for axis-aligned rectangles like CCD tiles.

## Implementation Overview
- Targets axis-aligned rectangles and builds a binary tree (Bounding Volume Hierarchy) based on center coordinates.
- Configurable maximum element count (`max_leaf_size`) in leaf nodes; recursively split until element count falls below threshold.
- Intersection tests with query rectangles traverse the tree and only check rectangle-to-rectangle intersection for necessary nodes,
  significantly reducing execution time compared to linear traversal.
- Input rectangles accept `BBox` or sequence format `(minx, miny, maxx, maxy)`.

## Public API
The `RectangleIndex` class is the entry point.

| Method | Description |
| --- | --- |
| `RectangleIndex(max_leaf_size: int = 16)` | Initialize the index. Specify maximum element count in leaf nodes. |
| `insert(identifier: int, bounds: BoundsLike)` | Register a single rectangle. Identifier is any integer and is returned in search results. |
| `bulk_load(items: Iterable[tuple[int, BoundsLike]])` | Register multiple rectangles together. Internally performs same validation as `insert`. |
| `intersection(bounds: BoundsLike) -> Iterator[int]` | Enumerate identifiers that intersect with the specified rectangle. |

Rectangle intersection is defined as overlap with closed intervals; matching boundaries also count as intersection.

## Usage Example
```python
from quicklook.utils.rtree import RectangleIndex

index = RectangleIndex()
index.bulk_load([
    (0, (0.0, 0.0, 10.0, 10.0)),
    (1, (5.0, 5.0, 15.0, 15.0)),
])

hits = list(index.intersection((8.0, 8.0, 12.0, 12.0)))
# => [1]
```

`TileInfo` uses this index to search CCD information.
Get a `RectangleIndex` instance from the `rtree_index()` function; it can be used with the same calling method as before.

## Cautions
- The index is built lazily. The tree is generated at the timing of the first query after `insert`/`bulk_load`.
- Rectangles specified in `BoundsLike` must satisfy `minx <= maxx` and `miny <= maxy`.
  If not satisfied, `ValueError` is raised.
- The existing `rtree` package is no longer needed, so we removed the dependency from `setup.py`.
