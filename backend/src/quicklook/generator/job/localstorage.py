import json
import shutil
from dataclasses import dataclass
from functools import cached_property
from pathlib import Path

from quicklook.config import config
from quicklook.job import Job
from quicklook.types import CcdId, Tile
from quicklook.utils.fitsheader import HeaderType
from quicklook.utils.numpyutils import ndarray2npybytes


@dataclass(frozen=True)
class JobLocalStorage:
    job: Job

    @cached_property
    def _base_dir(self):
        return Path(f'{config.job_local_dir}/{self.job.id}')

    def _fits_header_path(self, ccd_id: CcdId):
        return Path(f'{self._base_dir}/{ccd_id.fullname}.json')

    def save_fits_header(self, ccd_id: CcdId, headers: list[HeaderType]):
        path = self._fits_header_path(ccd_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('w') as f:
            json.dump(headers, f)

    def load_fits_header(self, ccd_id: CcdId) -> list[HeaderType]:
        path = self._fits_header_path(ccd_id)
        with path.open('r') as f:
            return json.load(f)

    def _single_fits_tile_path(self, ccd_id: CcdId, tile: Tile):
        return Path(f'{self._base_dir}/tiles/{tile.level}/{tile.i}/{tile.j}/{ccd_id.ccd_name}.npy')

    def save_single_fits_tile(self, ccd_id: CcdId, tile: Tile):
        outfile = self._single_fits_tile_path(ccd_id, tile)
        outfile.parent.mkdir(parents=True, exist_ok=True)
        outfile.write_bytes(ndarray2npybytes(tile.data))

    def remove_all(self):
        shutil.rmtree(self._base_dir, ignore_errors=True)
