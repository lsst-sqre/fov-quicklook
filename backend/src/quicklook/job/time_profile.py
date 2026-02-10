import time
from dataclasses import dataclass, field
from typing import Any

from quicklook.comm.types import GeneratorId
from quicklook.types import CcdName


@dataclass
class PhaseProfile:
    """1フェーズの所要時間を記録"""
    start_time: float = 0.0
    end_time: float = 0.0

    @property
    def elapsed(self) -> float:
        if self.start_time == 0.0 or self.end_time == 0.0:
            return 0.0
        return self.end_time - self.start_time

    def start(self):
        self.start_time = time.time()

    def finish(self):
        self.end_time = time.time()


@dataclass
class CcdProfile:
    """CCD 1枚の処理時間"""
    ccd_name: CcdName
    generator_id: GeneratorId
    elapsed: float


@dataclass
class GeneratorProfile:
    """Generator 1台の稼働時間"""
    generator_id: GeneratorId
    elapsed: float
    ccd_count: int


@dataclass
class TimeProfile:
    """パイプライン全体のプロファイル情報"""
    generate_single_fits_tiles: PhaseProfile = field(default_factory=PhaseProfile)
    merge_tiles: PhaseProfile = field(default_factory=PhaseProfile)
    upload_to_object_storage: PhaseProfile = field(default_factory=PhaseProfile)
    ccd_profiles: list[CcdProfile] = field(default_factory=list)
    generator_profiles: list[GeneratorProfile] = field(default_factory=list)

    def summary(self) -> dict[str, Any]:
        return {
            'generate_single_fits_tiles': self.generate_single_fits_tiles.elapsed,
            'merge_tiles': self.merge_tiles.elapsed,
            'upload_to_object_storage': self.upload_to_object_storage.elapsed,
            'total': sum([
                self.generate_single_fits_tiles.elapsed,
                self.merge_tiles.elapsed,
                self.upload_to_object_storage.elapsed,
            ]),
            'ccds': [
                {
                    'ccd_name': cp.ccd_name,
                    'generator_id': cp.generator_id,
                    'elapsed': cp.elapsed,
                }
                for cp in sorted(self.ccd_profiles, key=lambda cp: cp.elapsed, reverse=True)
            ],
            'generators': [
                {
                    'generator_id': gp.generator_id,
                    'elapsed': gp.elapsed,
                    'ccd_count': gp.ccd_count,
                }
                for gp in sorted(self.generator_profiles, key=lambda gp: gp.elapsed, reverse=True)
            ],
        }
