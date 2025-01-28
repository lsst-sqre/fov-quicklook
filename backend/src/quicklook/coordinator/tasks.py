import logging
from dataclasses import dataclass

from quicklook.config import config
from quicklook.datasource import get_datasource
from quicklook.types import GeneratorPod, Visit
from quicklook.utils.timeit import timeit


def make_generator_tasks(visit: Visit, generators: list[GeneratorPod]):
    ds = get_datasource()

    with timeit(f'Listing CCDs for visit {visit}', loglevel=logging.INFO):
        # ccds_for_visit = [*s3_list_visit_ccds(visit)]
        ccd_names_for_visit = [*ds.list_ccds(visit)]

    if config.dev_ccd_limit is not None:  # pragma: no cover
        ccd_names_for_visit = ccd_names_for_visit[: config.dev_ccd_limit]

    ng = len(generators)
    nc = len(ccd_names_for_visit)

    tasks: list[GeneratorTask] = []
    ccd_generator_map: dict[str, GeneratorPod] = {}

    for i, g in enumerate(generators):
        ccd_names = [ccd_name for ccd_name in ccd_names_for_visit[i * nc // ng : (i + 1) * nc // ng]]
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
