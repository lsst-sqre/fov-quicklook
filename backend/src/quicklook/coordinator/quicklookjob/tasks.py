from dataclasses import dataclass

from quicklook.types import GeneratorPod, Visit


@dataclass
class GenerateTask:
    generator: GeneratorPod
    visit: Visit
    ccd_names: list[str]
