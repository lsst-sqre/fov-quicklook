import logging
import shutil
from pathlib import Path

import numpy

from quicklook.config import config
from quicklook.types import CcdId, Tile, Visit
from quicklook.utils.numpyutils import ndarray2npybytes

logger = logging.getLogger(f'uviorn.{__name__}')


class TmpTile:
    def put_tile(self, ccd_id: CcdId, tile: Tile):
        outfile = Path(f'{config.tile_tmpdir}/{tile.visit.id}/tiles/{tile.level}/{tile.i}/{tile.j}/{ccd_id.ccd_name}.npy')
        outfile.parent.mkdir(parents=True, exist_ok=True)
        outfile.write_bytes(ndarray2npybytes(tile.data))

    def iter_tiles(self, visit: Visit):
        for p in Path(f'{config.tile_tmpdir}/{visit.id}/tiles').iterdir():
            if p.is_dir():  # pragma: no branch
                for q in p.iterdir():
                    if q.is_dir():  # pragma: no branch
                        for r in q.iterdir():
                            if r.is_dir():  # pragma: no branch
                                yield int(p.name), int(q.name), int(r.name)

    def get_tile_npy(self, visit: Visit, level: int, i: int, j: int) -> numpy.ndarray:
        pool: numpy.ndarray | None = None
        for path in Path(f'{config.tile_tmpdir}/{visit.id}/tiles/{level}/{i}/{j}').glob('*.npy'):
            arr = numpy.load(path)
            if pool is None:
                pool = arr
            else:
                pool += arr
        if pool is None:  # pragma: no cover
            pool = numpy.zeros((config.tile_size, config.tile_size), dtype=numpy.float32)
        return pool

    def delete_cache(self, visit: Visit):
        try:
            shutil.rmtree(Path(f'{config.tile_tmpdir}/{visit.id}'))
        except FileNotFoundError:
            pass

    def delete_all_cache(self):
        try:
            shutil.rmtree(Path(config.tile_tmpdir))
        except FileNotFoundError:
            pass


tmptile = TmpTile()
