from dataclasses import dataclass

from quicklook.types import GeneratorPod, Visit


@dataclass
class GenerateTask:
    visit: Visit
    generator: GeneratorPod
    ccd_names: list[str]


@dataclass
class MergeTask:
    visit: Visit
    generator: GeneratorPod
    ccd_generator_map: dict[str, GeneratorPod]


@dataclass
class TransferTask:
    visit: Visit
