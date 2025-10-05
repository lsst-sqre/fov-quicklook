from dataclasses import dataclass
from functools import cache, cached_property

from quicklook.comm.types import GeneratorId
from quicklook.job.job import Job
from quicklook.tileinfo import TileInfo
from quicklook.types import TilePos


@dataclass(frozen=True)
class GeneratorAssignment:
    job: Job
    pos: TilePos

    @cached_property
    def ccd_names(self):
        all_ccd_names = TileInfo.from_pos(self.pos).ccd_names
        return [ccd_name for ccd_name in all_ccd_names if ccd_name in self.dist_config.ccd_generator_map]

    @cached_property
    def dist_config(self):
        return self.job.local_storage.ccd_distribution_config.load()

    @cached_property
    def generator_ids(self) -> list[GeneratorId]:
        return sorted(set(self.dist_config.ccd_generator_map[ccd_name] for ccd_name in self.ccd_names))

    @cache
    def primary_generator_id(self) -> GeneratorId:
        if len(self.generator_ids) == 0:
            raise NoGeneratorFoundError(self.job, self.pos)
        index = self.pos.safe_hash() % len(self.generator_ids)
        return self.generator_ids[index]


class NoGeneratorFoundError(Exception):
    pass
