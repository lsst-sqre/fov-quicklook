import io
import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import astropy.io.fits as pyfits
import numpy
from astropy.utils.exceptions import AstropyUserWarning


def preload_pyfits_compression_code():
    # このコードを１度実行しておくと以降の展開が速くなる。
    # ベンチマーク用
    hdu = pyfits.CompImageHDU(numpy.array([[0.0]]))
    hdu.writeto(io.BytesIO(), output_verify='fix')


def fits_partial_load(
    read: Callable[[int, int], bytes],
    hdu_index: list[int],
) -> bytes:
    '''
    FITSファイルの一部を読み込む
    '''
    assert hdu_index == [0, 1]
    size = -1
    probe_pos = 1440 * 20
    while probe_pos < 500_000:
        f = io.BytesIO(read(0, probe_pos))
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", category=AstropyUserWarning)
            try:
                with pyfits.open(f) as hdul:  # type: ignore
                    # ここは内部実装によるのでastropyのバージョンが変わると動かなくなるかもしれない
                    # ローカルでは動くがk8sでは動かないなどの場合、ローカルでも `pip install -U -e .` などしてライブラリをアップデートすること
                    hdu = hdul[1]
                    size: int = hdu._data_offset + hdu._data_size  # type: ignore
                    # fi = hdul[1].fileinfo()  # type: ignore
                    # "hdrLoc": self._header_offset,
                    # "datLoc": self._data_offset,
                    # "datSpan": self._data_size,
                    # size: int = fi['datLoc'] + fi['datSpan']
                    break
            except (OSError, IndexError):
                # TODO: test: ここを通るテストを書く。テスト内でサンプルのFITSファイルを作る必要がある。
                pass
        probe_pos *= 2
    assert size >= 0
    return read(0, size)


@dataclass
class HduPosition:
    hdu_index: int
    start: int
    end: int
