from typing import Callable

import numpy

from quicklook.config import config
from quicklook.generator.preprocess_ccd import PreProcessedCcd
from quicklook.types import Tile, TilePos
from quicklook.utils.geom import BBox


def iterate_tiles(
    ppccd: PreProcessedCcd,
    cb: Callable[[Tile], None],
):
    tile_size = config.tile_size
    max_level = config.tile_max_level
    data = ppccd.pool
    h, w = data.shape[:2]
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
                cb(
                    Tile(
                        visit=ppccd.data_ref.visit,
                        pos=TilePos(level=level, i=tile_yi, j=tile_xi),
                        data=tile_data,
                    ),
                )
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
        return pool[y1 - pool_y1 : y2 - pool_y1, x1 - pool_x1 : x2 - pool_x1, :]
    zeros = numpy.zeros((y2 - y1, x2 - x1, 2), dtype=pool.dtype)
    x1_ = max(x1, pool_x1)
    y1_ = max(y1, pool_y1)
    x2_ = min(x2, pool_x1 + pool.shape[1])
    y2_ = min(y2, pool_y1 + pool.shape[0])
    zeros[y1_ - y1 : y2_ - y1, x1_ - x1 : x2_ - x1, :] = pool[
        y1_ - pool_y1 : y2_ - pool_y1,
        x1_ - pool_x1 : x2_ - pool_x1,
        :,
    ]
    return zeros


def shrink_image(
    data: numpy.ndarray,  # (H, W, 2): channel 0=value, channel 1=alpha
    y1: int,
    y2: int,
    x1: int,
    x2: int,
):
    pad_top = 1 if y1 != 0 else 0
    pad_bottom = 1 if y2 != 0 else 0
    pad_left = 1 if x1 != 0 else 0
    pad_right = 1 if x2 != 0 else 0

    if pad_top or pad_bottom or pad_left or pad_right:
        data = numpy.pad(
            data,
            ((pad_top, pad_bottom), (pad_left, pad_right), (0, 0)),
            mode='constant',
            constant_values=0,
        )

    h, w, _ = data.shape
    new_h, new_w = h // 2, w // 2

    # Premultiplied alpha: 両チャネルとも2x2ブロックの単純平均
    # channel 0 は premultiplied value (= value * alpha) なので単純平均で正しい
    result = data.reshape(new_h, 2, new_w, 2, 2).mean(axis=(1, 3))

    return result
