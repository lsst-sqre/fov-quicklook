import dataclasses
import functools
import json
import multiprocessing
from dataclasses import dataclass
from functools import cache
from pathlib import Path

import astropy.io.fits as afits
import rtree

from quicklook.config import config
from quicklook.types import BBox


@dataclass
class TileInfo:
    ccd_names: list[str]

    @classmethod
    def of(cls, level: int, i: int, j: int):
        tile_size = config.tile_size * (1 << level)
        bbox = BBox(
            minx=j * tile_size,
            miny=i * tile_size,
            maxx=(j + 1) * tile_size,
            maxy=(i + 1) * tile_size,
        )
        return TileInfo(ccd_names=[*ccds_intersecting(bbox)])


@dataclass
class Ccd:
    name: str
    bbox: BBox


def ccds_intersecting(bbox: BBox):
    for i in sorted([*rtree_index().intersection([bbox.minx, bbox.miny, bbox.maxx, bbox.maxy])]):
        yield ccd_list()[i].name


ccd_info_path = Path(__file__).parent / 'ccd-info.json'


@cache
def ccd_list():
    ccds: list[Ccd] = [Ccd(name=e['name'], bbox=BBox(**e['bbox'])) for e in json.loads(ccd_info_path.read_text())]
    return ccds


@cache
def ccds_by_name():
    return {ccd.name: ccd for ccd in ccd_list()}


@cache
def rtree_index():
    index = rtree.index.Index()
    for i, ccd in enumerate(ccd_list()):
        index.insert(i, [ccd.bbox.minx, ccd.bbox.miny, ccd.bbox.maxx, ccd.bbox.maxy])
    return index


if __name__ == '__main__':  # pragma: no cover

    def regenerate_ccd_info(
        srcdir: Path = Path('/home/michitaro/rubinviewer/data/shots/20230511PH'),
    ):
        fits_list = sorted(srcdir.glob('*.fits'))
        with multiprocessing.Pool() as pool:
            ccds = pool.map(_make_ccd_meta, fits_list)
        ccd_info_path.write_text(json.dumps(ccds, indent=2))

    def _make_ccd_meta(p: Path):
        from .generator.preprocess_ccd import RawAmp

        with afits.open(p, memmap=False) as hdul:
            amps = [RawAmp.from_hdu(j, hdu) for j, hdu in enumerate(hdul) if hdu.name.startswith('Segment')]  # type: ignore
            bbox = functools.reduce(lambda a, b: a.union(b.wcs.bbox), amps[1:], amps[0].wcs.bbox)
            header = hdul[0].header  # type: ignore
            ccd_name = f'{header["RAFTBAY"]}_{header["CCDSLOT"]}'
            return dict(name=ccd_name, bbox=dataclasses.asdict(bbox))

    regenerate_ccd_info()
