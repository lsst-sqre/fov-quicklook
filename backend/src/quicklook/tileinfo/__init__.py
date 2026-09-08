import dataclasses
import functools
import json
import multiprocessing
from dataclasses import dataclass
from functools import cache
from pathlib import Path

import astropy.io.fits as afits

from quicklook.config import config
from quicklook.types import CcdName, TilePos
from quicklook.utils.geom import BBox
from quicklook.utils.rtree import RectangleIndex
from quicklook.utils.wcs import FitsWcsHeader

ccd_info_path = Path(__file__).parent / 'ccd-info.json'

# LSST Camera 焦点面の WCS パラメータ
# pixel_scale: 1ピクセルあたりの角度 [arcsec/pixel]
FOCAL_PLANE_PIXEL_SCALE_ARCSEC = 0.2
FOCAL_PLANE_NAXIS1 = 63424
FOCAL_PLANE_NAXIS2 = 63376
FOCAL_PLANE_CRPIX1 = 31750.5
FOCAL_PLANE_CRPIX2 = 31750.5


@dataclass
class TileInfo:
    """LSST Camの焦点面のタイル情報を管理するクラス.

    タイルは規則正しく格子状に敷き詰められており、CCDの配置とタイルの配置は独立している。
    このクラスはとあるタイルに対して作られるインスタンスで、そのタイルとオーバーラップする
    CCDの情報を提供する。

    タイルにはレベルという概念がある：
    - レベル0: 最も細かいタイル（基準サイズ）
    - レベルが1上がるごとにタイルの一辺の長さが2倍になる
    """

    ccd_names: list[CcdName]
    level: int
    i: int  # タイルの行インデックス
    j: int  # タイルの列インデックス

    @classmethod
    def from_pos(cls, pos: TilePos) -> 'TileInfo':
        return cls._of(level=pos.level, i=pos.i, j=pos.j)

    @classmethod
    def _of(cls, level: int, i: int, j: int) -> 'TileInfo':
        """指定されたレベルと位置のタイル情報を作成する.

        Args:
            level: タイルのレベル（0が最も細かい）
            i: タイルの行インデックス
            j: タイルの列インデックス

        Returns:
            TileInfo: タイル情報のインスタンス
        """
        tile_size = config.tile_size * (1 << level)
        bbox = BBox(
            minx=j * tile_size,
            miny=i * tile_size,
            maxx=(j + 1) * tile_size,
            maxy=(i + 1) * tile_size,
        )
        ccd_names = list(ccds_intersecting(bbox))
        return cls(ccd_names=ccd_names, level=level, i=i, j=j)

    @property
    def tile_size(self) -> int:
        """このタイルのサイズ（一辺の長さ）を取得する."""
        return config.tile_size * (1 << self.level)

    @property
    def bbox(self) -> BBox:
        """このタイルの境界ボックスを取得する."""
        tile_size = self.tile_size
        return BBox(
            minx=self.j * tile_size,
            miny=self.i * tile_size,
            maxx=(self.j + 1) * tile_size,
            maxy=(self.i + 1) * tile_size,
        )

    def get_overlapping_ccds(self) -> list['_Ccd']:
        """このタイルとオーバーラップするCCDのリストを取得する."""
        ccds_dict = ccds_by_name()
        return [ccds_dict[name] for name in self.ccd_names if name in ccds_dict]


@dataclass
class _Ccd:
    """CCDの情報を表す内部クラス."""

    name: CcdName
    bbox: BBox


def ccds_intersecting(bbox: BBox) -> list[CcdName]:
    """指定された境界ボックスと交差するCCD名のリストを取得する.

    Args:
        bbox: 交差判定を行う境界ボックス

    Returns:
        交差するCCD名のリスト
    """
    ccd_indices = rtree_index().intersection([bbox.minx, bbox.miny, bbox.maxx, bbox.maxy])
    ccds = ccd_list()
    return [ccds[i].name for i in ccd_indices]


@cache
def ccd_list() -> list[_Ccd]:
    """ccd-info.jsonからCCDのリストを読み込む.

    Returns:
        CCDの情報のリスト

    Raises:
        FileNotFoundError: ccd-info.jsonが見つからない場合
        json.JSONDecodeError: JSONの形式が不正な場合
    """
    if not ccd_info_path.exists():
        raise FileNotFoundError(f"CCD情報ファイルが見つかりません: {ccd_info_path}")

    try:
        data = json.loads(ccd_info_path.read_text())
        return [_Ccd(name=CcdName(e['name']), bbox=BBox(**e['bbox'])) for e in data]
    except json.JSONDecodeError as e:
        raise json.JSONDecodeError(f"CCD情報ファイルの形式が不正です: {e}", e.doc, e.pos) from e
    except KeyError as e:
        raise ValueError(f"CCD情報ファイルに必要なキーがありません: {e}") from e


@cache
def ccds_by_name() -> dict[str, _Ccd]:
    """CCD名をキーとした辞書を取得する.

    Returns:
        CCD名をキーとしたCCD情報の辞書
    """
    return {ccd.name: ccd for ccd in ccd_list()}


@cache
def rtree_index() -> RectangleIndex:
    """CCD検索用の矩形インデックスを取得する."""

    index = RectangleIndex()
    index.bulk_load(
        (
            i,
            (
                ccd.bbox.minx,
                ccd.bbox.miny,
                ccd.bbox.maxx,
                ccd.bbox.maxy,
            ),
        )
        for i, ccd in enumerate(ccd_list())
    )
    return index


if __name__ == '__main__':  # pragma: no cover

    def regenerate_ccd_info(
        srcdir: Path = Path('../sample-data/20230511PH'),
    ):
        fits_list = sorted(srcdir.glob('*.fits'))
        with multiprocessing.Pool() as pool:
            ccds = pool.map(_make_ccd_meta, fits_list)
        ccd_info_path.write_text(json.dumps(ccds, indent=2))

    def _make_ccd_meta(p: Path):
        from quicklook.generator.preprocess_ccd import RawAmp

        with afits.open(p, memmap=False) as hdul:  # type: ignore
            amps = [RawAmp.from_hdu(j, hdu) for j, hdu in enumerate(hdul) if hdu.name.startswith('Segment')]  # type: ignore
            bbox = functools.reduce(lambda a, b: a.union(b.wcs.bbox), amps[1:], amps[0].wcs.bbox)
            header = hdul[0].header  # type: ignore
            ccd_name = f'{header["RAFTBAY"]}_{header["CCDSLOT"]}'
            return dict(name=ccd_name, bbox=dataclasses.asdict(bbox))

    regenerate_ccd_info()


def focal_plane_wcs() -> FitsWcsHeader:
    """焦点面全体の WCS パラメータを返す（TAN投影）"""
    scale = FOCAL_PLANE_PIXEL_SCALE_ARCSEC / 3600.0  # arcsec → degree
    return FitsWcsHeader(
        NAXIS1=FOCAL_PLANE_NAXIS1,
        NAXIS2=FOCAL_PLANE_NAXIS2,
        CRVAL1=0,
        CRVAL2=0,
        CRPIX1=FOCAL_PLANE_CRPIX1,
        CRPIX2=FOCAL_PLANE_CRPIX2,
        CD1_1=-scale,
        CD1_2=0,
        CD2_1=0,
        CD2_2=scale,
    )
