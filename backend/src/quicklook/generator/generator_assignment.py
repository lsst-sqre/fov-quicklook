from dataclasses import dataclass
from functools import cache, cached_property

from quicklook.comm.types import GeneratorId
from quicklook.job.job import Job
from quicklook.job.local_storage import CcdDistributionConfig
from quicklook.tileinfo import TileInfo
from quicklook.types import TilePos


@dataclass(frozen=True)
class GeneratorAssignment:
    pos: TilePos
    dist_config: CcdDistributionConfig

    @classmethod
    def from_job_and_pos(cls, job: Job, pos: TilePos) -> 'GeneratorAssignment':
        return cls(pos=pos, dist_config=job.local_storage.ccd_distribution_config.load())

    @cached_property
    def ccd_names(self):
        all_ccd_names = TileInfo.from_pos(self.pos).ccd_names
        return [ccd_name for ccd_name in all_ccd_names if ccd_name in self.dist_config.ccd_generator_map]

    @cached_property
    def generator_ids(self) -> list[GeneratorId]:
        return sorted(set(self.dist_config.ccd_generator_map[ccd_name] for ccd_name in self.ccd_names))

    @cached_property
    def primary_generator_id(self) -> GeneratorId:
        if len(self.generator_ids) == 0:
            raise NoGeneratorFoundError()
        index = self.pos.safe_hash() % len(self.generator_ids)
        return self.generator_ids[index]


class NoGeneratorFoundError(RuntimeError):
    pass
