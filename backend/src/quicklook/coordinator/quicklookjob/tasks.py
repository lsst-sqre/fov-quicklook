from dataclasses import dataclass

from quicklook.types import GeneratorPod, Visit


@dataclass
class GeneratorTask:
    generator: GeneratorPod
    visit: Visit
    ccd_names: list[str]
    ccd_generator_map: dict[str, GeneratorPod]
