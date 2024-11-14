import logging
from dataclasses import dataclass

from quicklook.config import config
from quicklook.storage import s3_list_visit_ccds
from quicklook.types import GeneratorPod, Visit
from quicklook.utils.timeit import timeit


def make_generator_tasks(visit: Visit, generators: list[GeneratorPod]):
    with timeit(f'Listing CCDs for visit {visit}', loglevel=logging.INFO):
        ccds_for_visit = [*s3_list_visit_ccds(visit)]

    if config.dev_ccd_limit is not None:  # pragma: no cover
        ccds_for_visit = ccds_for_visit[: config.dev_ccd_limit]

    ng = len(generators)
    nc = len(ccds_for_visit)

    tasks: list[GeneratorTask] = []
    ccd_generator_map: dict[str, GeneratorPod] = {}

    for i, g in enumerate(generators):
        ccd_names = [ccd.ccd_id.ccd_name for ccd in ccds_for_visit[i * nc // ng : (i + 1) * nc // ng]]
        task = GeneratorTask(generator=g, visit=visit, ccd_names=ccd_names, ccd_generator_map=ccd_generator_map)
        tasks.append(task)
        for ccd_name in ccd_names:
            ccd_generator_map[ccd_name] = g

    return tasks


@dataclass
class GeneratorTask:
    generator: GeneratorPod
    visit: Visit
    ccd_names: list[str]
    ccd_generator_map: dict[str, GeneratorPod]
