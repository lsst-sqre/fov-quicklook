import pickle
import shutil
from dataclasses import dataclass
from functools import cached_property
from pathlib import Path

import numpy

from quicklook.comm.generator import self_generator_id
from quicklook.comm.types import GeneratorInfo
from quicklook.config import config
from quicklook.generator.job import Job
from quicklook.tileinfo import TileInfo
from quicklook.types import CcdId, Tile, TilePos
from quicklook.utils.fitsheader import HeaderType
from quicklook.utils.numpyutils import ndarray2npybytes, npybytes2ndarray


class JobStorage:
    job_id: str

    def __init__(self, job: Job):
        self.job_id = job.id

    @cached_property
    def base_dir(self):
        return Path(f'{config.job_local_dir}/{self.job_id}/{self_generator_id()}')

    @cached_property
    def fits_header(self):
        return _FitsHeaderStorage(self)

    @cached_property
    def single_fits_tile(self):
        return _SingleFitsTileStorage(self)

    @cached_property
    def ccd_distribution_config(self):
        return _CcdDistributionConfigStorage(self)

    @cached_property
    def merged_fits_tile(self):
        return _MergedFitsTileStorage(self)

    def clear_all(self):
        shutil.rmtree(self.base_dir, ignore_errors=True)


@dataclass
class _FitsHeaderStorage:
    storage: JobStorage

    def _path(self, ccd_id: CcdId):
        return Path(f'{self.storage.base_dir}/fits_header/{ccd_id.ccd_name}.pickle')

    def save(self, ccd_id: CcdId, headers: list[HeaderType]):
        path = self._path(ccd_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('wb') as f:
            pickle.dump(headers, f)

    def load(self, ccd_id: CcdId) -> list[HeaderType]:
        path = self._path(ccd_id)
        with path.open('rb') as f:
            return pickle.load(f)


@dataclass
class CcdDistributionConfig:
    ccd_generator_map: dict[str, str]
    generators: dict[str, GeneratorInfo]


@dataclass
class _CcdDistributionConfigStorage:
    storage: JobStorage

    def save(self, config: CcdDistributionConfig):
        path = f'{self.storage.base_dir}/ccd_distribution_config.pickle'
        with open(path, 'wb') as f:
            pickle.dump(config, f)

    def load(self) -> CcdDistributionConfig:
        path = f'{self.storage.base_dir}/ccd_distribution_config.pickle'
        with open(path, 'rb') as f:
            return pickle.load(f)


@dataclass
class _SingleFitsTileStorage:
    storage: JobStorage

    def _path(self, ccd_name: str, pos: TilePos):
        return Path(f'{self.storage.base_dir}/tiles/{pos.level}/{pos.i}/{pos.j}/{ccd_name}.npy')

    def save(self, ccd_name: str, tile: Tile):
        outfile = self._path(ccd_name, tile.pos)
        outfile.parent.mkdir(parents=True, exist_ok=True)
        outfile.write_bytes(ndarray2npybytes(tile.data))

    def _load(self, ccd_name: str, pos: TilePos) -> numpy.ndarray:
        infile = self._path(ccd_name, pos)
        return npybytes2ndarray(infile.read_bytes())

    def _my_ccd_names(self, pos: TilePos):
        dist_config = self.storage.ccd_distribution_config.load()
        for ccd_name in TileInfo.from_pos(pos).ccd_names:
            if dist_config.ccd_generator_map.get(ccd_name) == self_generator_id():
                yield ccd_name

    def load_local_merged(self, pos: TilePos, ccd_names: list[str] | None = None) -> numpy.ndarray:
        merged = None
        if ccd_names is None:
            ccd_names = [*self._my_ccd_names(pos)]
        for ccd_name in ccd_names:
            data = self._load(ccd_name, pos)
            if merged is None:
                merged = data
            else:
                merged += data
        if merged is None:  # pragma: no cover
            # CcdInfo.ofが多少の誤差があるようなので。
            merged = numpy.zeros((config.tile_size, config.tile_size), dtype=numpy.float32)
        return merged

    def iter_tiles(self):
        for p in Path(f'{self.storage.base_dir}/tiles').iterdir():
            if p.is_dir():  # pragma: no branch
                for q in p.iterdir():
                    if q.is_dir():  # pragma: no branch
                        for r in q.iterdir():
                            if r.is_dir():  # pragma: no branch
                                yield TilePos(level=int(p.name), i=int(q.name), j=int(r.name))

    def clear(self):
        shutil.rmtree(f'{self.storage.base_dir}/tiles', ignore_errors=True)


@dataclass
class _MergedFitsTileStorage:
    storage: JobStorage

    def _path(self, pos: TilePos):
        return Path(f'{self.storage.base_dir}/merged_tiles/{pos.level}/{pos.i}/{pos.j}.npy')

    def save_compressed_data(self, pos: TilePos, compressed_data: bytes):
        outfile = self._path(pos)
        outfile.parent.mkdir(parents=True, exist_ok=True)
        outfile.write_bytes(compressed_data)

    def load_compressed_data(self, pos: TilePos) -> bytes:
        infile = self._path(pos)
        return infile.read_bytes()
