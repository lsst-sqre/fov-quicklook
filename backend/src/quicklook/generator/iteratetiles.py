from typing import Callable

import numpy

from quicklook.config import config
from quicklook.types import PreProcessedCcd, Progress, Tile


def iterate_tiles(
    ppccd: PreProcessedCcd,
    cb: Callable[[Tile, Progress], None],
):
    progress = Progress(
        count=0,
        total=calc_num_total_tiles(ppccd),
    )
    tile_size = config.tile_size
    max_level = config.tile_max_level
    data = ppccd.pool
    h, w = data.shape
    y1 = int(ppccd.bbox.miny)  # focal planeでの始まりのy-index
    x1 = int(ppccd.bbox.minx)
    y2 = int(y1 + h)  # 終わりのindex
    x2 = int(x1 + w)
    for level in range(max_level + 1):  # pragma: no branch
        tile_yi1 = y1 // tile_size
        tile_yi2 = (y2 - 1) // tile_size + 1
        tile_xi1 = x1 // tile_size
        tile_xi2 = (x2 - 1) // tile_size + 1
        for tile_yi in range(tile_yi1, tile_yi2):
            tile_y1 = tile_yi * tile_size
            tile_y2 = tile_y1 + tile_size
            for tile_xi in range(tile_xi1, tile_xi2):
                tile_x1 = tile_xi * tile_size
                tile_x2 = tile_x1 + tile_size
                tile_data = safe_slice(data, x1, y1, tile_x1, tile_y1, tile_x2, tile_y2)
                progress.count += 1
                cb(Tile(visit=ppccd.ccd_id.visit, level=level, i=tile_yi, j=tile_xi, data=tile_data), progress)
        if level >= max_level:
            break
        data = shrink_image(data, y1 % 2, y2 % 2, x1 % 2, x2 % 2)
        if y1 % 2 != 0:
            y1 -= 1
        if y2 % 2 != 0:
            y2 += 1
        if x1 % 2 != 0:
            x1 -= 1
        if x2 % 2 != 0:
            x2 += 1
        y1 //= 2
        x1 //= 2
        y2 //= 2
        x2 //= 2


def safe_slice(
    pool: numpy.ndarray,
    pool_x1: int,  # focal planeでの始まりのx-index
    pool_y1: int,
    x1: int,  # tileでの始まりのx-index
    y1: int,
    x2: int,  # tileでの終わりのx-index
    y2: int,
):
    if x1 >= pool_x1 and y1 >= pool_y1 and x2 <= pool_x1 + pool.shape[1] and y2 <= pool_y1 + pool.shape[0]:
        return pool[y1 - pool_y1 : y2 - pool_y1, x1 - pool_x1 : x2 - pool_x1]
    zeros = numpy.zeros((y2 - y1, x2 - x1), dtype=pool.dtype)
    x1_ = max(x1, pool_x1)
    y1_ = max(y1, pool_y1)
    x2_ = min(x2, pool_x1 + pool.shape[1])
    y2_ = min(y2, pool_y1 + pool.shape[0])
    zeros[y1_ - y1 : y2_ - y1, x1_ - x1 : x2_ - x1] = pool[
        y1_ - pool_y1 : y2_ - pool_y1,
        x1_ - pool_x1 : x2_ - pool_x1,
    ]
    return zeros


def shrink_image(
    data: numpy.ndarray,  # 2D array
    y1: int,
    y2: int,
    x1: int,
    x2: int,
):
    if y1 != 0:
        data = numpy.vstack((numpy.zeros(data.shape[1], dtype=numpy.float32), data))
    if y2 != 0:
        data = numpy.vstack((data, numpy.zeros(data.shape[1], dtype=numpy.float32)))
    if x1 != 0:
        data = numpy.hstack((numpy.zeros((data.shape[0], 1), dtype=numpy.float32), data))
    if x2 != 0:
        data = numpy.hstack((data, numpy.zeros((data.shape[0], 1), dtype=numpy.float32)))
    h, w = data.shape
    data = numpy.mean(data.reshape(h // 2, 2, w // 2, 2), axis=(1, 3))
    return data


def calc_num_total_tiles(
    ccd: PreProcessedCcd,
):
    tile_size = config.tile_size
    max_level = config.tile_max_level
    data = ccd.pool
    h, w = data.shape
    y1 = int(ccd.bbox.miny)  # focal planeでの始まりのy-index
    x1 = int(ccd.bbox.minx)
    y2 = int(y1 + h)  # 終わりのindex
    x2 = int(x1 + w)
    num_tiles = 0
    for _ in range(max_level + 1):
        tile_yi1 = y1 // tile_size
        tile_yi2 = (y2 - 1) // tile_size + 1
        tile_xi1 = x1 // tile_size
        tile_xi2 = (x2 - 1) // tile_size + 1
        num_tiles += (tile_yi2 - tile_yi1) * (tile_xi2 - tile_xi1)
        if y1 % 2 != 0:
            y1 -= 1
        if y2 % 2 != 0:
            y2 += 1
        y1 //= 2
        y2 //= 2
        if x1 % 2 != 0:
            x1 -= 1
        if x2 % 2 != 0:
            x2 += 1
        x1 //= 2
        x2 //= 2
    return num_tiles
