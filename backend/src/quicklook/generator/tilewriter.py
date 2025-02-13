from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from quicklook.config import config
from quicklook.types import CcdId, Tile
from quicklook.utils.exitstack import exit_stack
from quicklook.utils.numpyutils import ndarray2npybytes
import shutil


class TileWriterBase(Protocol):
    def put(self, tile: Tile, *, fragment: bool): ...  # pragma no branch


@dataclass
class TileWriter(TileWriterBase):
    ccd_id: CcdId

    def __post_init__(self):
        pass

    def __enter__(self):
        with exit_stack() as self._exit_stack:
            return self

    def __exit__(self, exc_type, exc_value, traceback):
        self._exit_stack.close()

    def put(self, tile: Tile, *, fragment: bool):
        outfile = Path(f'{config.tile_tmpdir}/{self.ccd_id.name}/{tile.level}/{tile.i}/{tile.j}.npy')
        outfile.parent.mkdir(parents=True, exist_ok=True)
        outfile.write_bytes(ndarray2npybytes(tile.data))

    @classmethod
    def delete_all_cache(cls):
        try:
            shutil.rmtree(Path(config.tile_tmpdir))
        except FileNotFoundError:
            pass
