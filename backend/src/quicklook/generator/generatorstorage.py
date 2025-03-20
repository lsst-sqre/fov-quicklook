import logging
import shutil
from pathlib import Path
from typing import Generator

import numpy

from quicklook.config import config
from quicklook.types import CcdId, Tile, Visit
from quicklook.utils.numpyutils import ndarray2npybytes

logger = logging.getLogger(f'uviorn.{__name__}')


class _GeneratorTmpTile:
    def put_tile(self, ccd_id: CcdId, tile: Tile):
        outfile = Path(f'{self.visit_dir(tile.visit)}/tiles/{tile.level}/{tile.i}/{tile.j}/{ccd_id.ccd_name}.npy')
        outfile.parent.mkdir(parents=True, exist_ok=True)
        outfile.write_bytes(ndarray2npybytes(tile.data))

    def iter_tiles(self, visit: Visit) -> Generator[tuple[int, int, int], None, None]:
        for p in Path(f'{config.tile_tmpdir}/{visit.id}/tiles').iterdir():
            if p.is_dir():  # pragma: no branch
                for q in p.iterdir():
                    if q.is_dir():  # pragma: no branch
                        for r in q.iterdir():
                            if r.is_dir():  # pragma: no branch
                                yield int(p.name), int(q.name), int(r.name)

    def visit_dir(self, visit: Visit):
        return Path(f'{config.tile_tmpdir}/{visit.id}')

    def get_tile_npy(self, visit: Visit, level: int, i: int, j: int) -> numpy.ndarray:
        pool: numpy.ndarray | None = None
        for path in Path(f'{self.visit_dir(visit)}/tiles/{level}/{i}/{j}').glob('*.npy'):
            arr = numpy.load(path)
            if pool is None:
                pool = arr
            else:
                pool += arr
        if pool is None:  # pragma: no cover
            pool = numpy.zeros((config.tile_size, config.tile_size), dtype=numpy.float32)
        return pool

    def delete(self, visit: Visit):
        try:
            shutil.rmtree(Path(f'{config.tile_tmpdir}/{visit.id}'))
        except FileNotFoundError:
            pass

    def delete_all(self):
        try:
            shutil.rmtree(Path(config.tile_tmpdir))
        except FileNotFoundError:
            pass


class _GeneratorMergedTile:
    def put_tile_data(self, visit: Visit, level: int, i: int, j: int, data: bytes):
        outfile = Path(f'{config.tile_merged_dir}/{visit.id}/{level}/{i}/{j}.npy.zstd')
        outfile.parent.mkdir(parents=True, exist_ok=True)
        with open(outfile, 'wb') as f:
            f.write(data)

    def get_tile_data(self, visit: Visit, level: int, i: int, j: int) -> bytes:
        infile = Path(f'{config.tile_merged_dir}/{visit.id}/{level}/{i}/{j}.npy.zstd')
        if not infile.exists():
            raise FileNotFoundError(f'{infile} not found')
        return infile.read_bytes()

    def iter_tiles(self, visit: Visit) -> Generator[tuple[int, int, int], None, None]:
        for p in Path(f'{config.tile_merged_dir}/{visit.id}').iterdir():
            if p.is_dir():
                for q in p.iterdir():
                    if q.is_dir():
                        for r in q.iterdir():
                            if r.is_file():
                                # r は 3.npy.zstd のようなファイル名
                                yield int(p.name), int(q.name), int(r.name.split('.')[0])


tmptile_storage = _GeneratorTmpTile()
mergedtile_storage = _GeneratorMergedTile()
