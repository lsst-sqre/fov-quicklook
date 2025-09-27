import logging
import pickle
import shutil
from dataclasses import dataclass
from functools import cache, cached_property, lru_cache
from pathlib import Path

import numpy

from quicklook.comm.generator import self_generator_id
from quicklook.comm.types import GeneratorInfo
from quicklook.config import config
from quicklook.generator.job import Job
from quicklook.tileinfo import TileInfo
from quicklook.types import CcdDataRef, CcdName, Tile, TilePos
from quicklook.utils.fitsheader import HeaderType
from quicklook.utils.numpyutils import ndarray2npybytes, npybytes2ndarray


@dataclass(frozen=True)
class JobLocalStorage:
    job: Job

    @classmethod
    @lru_cache(config.max_job)
    def from_job(cls, job: Job) -> 'JobLocalStorage':
        return cls(job)

    @classmethod
    def from_id(cls, job_id: str) -> 'JobLocalStorage':
        job = _JobMetadataStorage.load_job(job_id)
        return cls.from_job(job)

    @staticmethod
    def _base_dir_for(job_id: str) -> Path:
        return Path(f'{config.job_local_dir}/{job_id}/{self_generator_id()}')

    @cached_property
    def base_dir(self):
        return self._base_dir_for(self.job.id)

    @cached_property
    def metadata(self):
        return _JobMetadataStorage(self)

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

    @cached_property
    def logger(self) -> logging.Logger:
        logger_name = f'{__name__}.{self.job.id}'
        logger = logging.getLogger(logger_name)

        if not logger.handlers:
            log_path = self.base_dir / 'log'
            self.base_dir.mkdir(parents=True, exist_ok=True)
            handler = logging.FileHandler(log_path, encoding='utf-8')
            formatter = logging.Formatter('%(asctime)s %(levelname)s %(name)s %(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)
            logger.propagate = False

        return logger

    def clear_all(self):
        shutil.rmtree(self.base_dir, ignore_errors=True)


@dataclass
class _FitsHeaderStorage:
    storage: JobLocalStorage

    def _path(self, ccd_ref: CcdDataRef):
        return Path(f'{self.storage.base_dir}/fits_header/{ccd_ref.ccd}.pickle')

    def save(self, ccd_ref: CcdDataRef, headers: list[HeaderType]):
        path = self._path(ccd_ref)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('wb') as f:
            pickle.dump(headers, f)

    def load(self, ccd_ref: CcdDataRef) -> list[HeaderType]:
        path = self._path(ccd_ref)
        with path.open('rb') as f:
            return pickle.load(f)


@dataclass
class CcdDistributionConfig:
    ccd_generator_map: dict[CcdName, str]
    generators: dict[str, GeneratorInfo]


@dataclass(frozen=True)
class _CcdDistributionConfigStorage:
    storage: JobLocalStorage

    def _path(self):
        return Path(f'{self.storage.base_dir}/ccd_distribution_config.pickle')

    def save(self, config: CcdDistributionConfig):
        path = self._path()
        with open(path, 'wb') as f:
            pickle.dump(config, f)

    @cache
    def load(self) -> CcdDistributionConfig:
        with open(self._path(), 'rb') as f:
            return pickle.load(f)


@dataclass
class _SingleFitsTileStorage:
    storage: JobLocalStorage

    def _path(self, ccd_name: CcdName, pos: TilePos):
        return Path(f'{self.storage.base_dir}/tiles/{pos.level}/{pos.i}/{pos.j}/{ccd_name}.npy')

    def save(self, ccd_name: CcdName, tile: Tile):
        outfile = self._path(ccd_name, tile.pos)
        outfile.parent.mkdir(parents=True, exist_ok=True)
        outfile.write_bytes(ndarray2npybytes(tile.data))

    def _load(self, ccd_name: CcdName, pos: TilePos) -> numpy.ndarray:
        infile = self._path(ccd_name, pos)
        return npybytes2ndarray(infile.read_bytes())

    def _my_ccd_names(self, pos: TilePos):
        dist_config = self.storage.ccd_distribution_config.load()
        for ccd_name in TileInfo.from_pos(pos).ccd_names:
            name = CcdName(ccd_name)
            if dist_config.ccd_generator_map.get(name) == self_generator_id():
                yield name

    def load_local_merged(self, pos: TilePos, ccd_names: list[CcdName] | None = None) -> numpy.ndarray:
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
    storage: JobLocalStorage

    def _path(self, pos: TilePos):
        return Path(f'{self.storage.base_dir}/merged_tiles/{pos.level}/{pos.i}/{pos.j}.npy')

    def save_compressed_data(self, pos: TilePos, compressed_data: bytes):
        outfile = self._path(pos)
        outfile.parent.mkdir(parents=True, exist_ok=True)
        outfile.write_bytes(compressed_data)

    def load_compressed_data(self, pos: TilePos) -> bytes:
        infile = self._path(pos)
        if not infile.exists():
            raise FileNotFoundError(f'Merged FITS tile not found: {infile}')
        return infile.read_bytes()


@dataclass
class _JobMetadataStorage:
    storage: JobLocalStorage

    @classmethod
    def _path(cls, job_id: str) -> Path:
        return JobLocalStorage._base_dir_for(job_id) / 'metadata.pickle'

    def save(self):
        job = self.storage.job
        path = self._path(job.id)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(pickle.dumps(job))

    @classmethod
    @lru_cache(config.max_job)
    def load_job(cls, job_id: str) -> Job:
        path = cls._path(job_id)
        job = pickle.loads(path.read_bytes())
        return job
