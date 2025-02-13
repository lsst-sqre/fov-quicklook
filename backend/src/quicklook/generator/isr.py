import operator
from dataclasses import dataclass
from typing import TypeAlias

import numpy

DataSection: TypeAlias = tuple[tuple[int, int], tuple[int, int]]


@dataclass
class IsrConfig:
    do_col_bias: bool = True
    do_row_bias: bool = True


def bias_correction(data: numpy.ndarray, datasec: DataSection, config: IsrConfig = IsrConfig()):
    (x1, x2), (y1, y2) = datasec
    assert x1 < x2
    assert y1 < y2
    # h, w = hdu.data.shape
    data = numpy.array(data, dtype=numpy.float32)
    # assert config.do_row_bias is False
    if config.do_row_bias:
        row_bias = data[:, x2:].mean(axis=1)
        operator.isub(data.T, row_bias)
        # ↑ is equivalent to ↓
        # data -= numpy.repeat(row_bias.reshape((-1, 1)), w, axis=1)
    if config.do_col_bias:  # pragma: no branch
        col_bias = data[y2 - 1 :, :].mean(axis=0)
        data -= col_bias
    return data[y1 - 1 : y2, x1 - 1 : x2]


def parse_slice(s: str) -> DataSection:
    # [509:1,1:2000]
    return DataSection(tuple(int(n) for n in se.split(':')) for se in s[1:-1].split(','))  # type: ignore
