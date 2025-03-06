from pathlib import Path

from quicklook.config import config
from quicklook.types import CcdId, Tile
from quicklook.utils.numpyutils import ndarray2npybytes
import shutil


class TmpTile:
    @classmethod
    def put(cls, ccd_id: CcdId, tile: Tile):
        outfile = Path(f'{config.tile_tmpdir}/{ccd_id.name}/{tile.level}/{tile.i}/{tile.j}.npy')
        outfile.parent.mkdir(parents=True, exist_ok=True)
        outfile.write_bytes(ndarray2npybytes(tile.data))

    @classmethod
    def path(cls, ccd_id: CcdId, level: int, i: int, j: int) -> Path:
        return Path(f'{config.tile_tmpdir}/{ccd_id.name}/{level}/{i}/{j}.npy')

    @classmethod
    def delete_all_cache(cls):
        try:
            shutil.rmtree(Path(config.tile_tmpdir))
        except FileNotFoundError:
            pass
