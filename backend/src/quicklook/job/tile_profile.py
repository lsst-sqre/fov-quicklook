import time
from dataclasses import dataclass, field


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
class TileProfile:
    """パイプライン全体のプロファイル情報"""
    generate_single_fits_tiles: PhaseProfile = field(default_factory=PhaseProfile)
    merge_tiles: PhaseProfile = field(default_factory=PhaseProfile)
    upload_to_object_storage: PhaseProfile = field(default_factory=PhaseProfile)

    def summary(self) -> dict[str, float]:
        return {
            'generate_single_fits_tiles': self.generate_single_fits_tiles.elapsed,
            'merge_tiles': self.merge_tiles.elapsed,
            'upload_to_object_storage': self.upload_to_object_storage.elapsed,
            'total': sum([
                self.generate_single_fits_tiles.elapsed,
                self.merge_tiles.elapsed,
                self.upload_to_object_storage.elapsed,
            ]),
        }
