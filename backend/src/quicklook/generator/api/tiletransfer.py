from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from logging import getLogger
from typing import Callable

from quicklook import storage
from quicklook.coordinator.quicklookjob.tasks import TransferTask
from quicklook.generator.generatorstorage import mergedtile_storage
from quicklook.types import TransferProgress, Progress, TransferTaskResponse, Visit
from quicklook.utils import throttle
from quicklook.utils.timeit import timeit

logger = getLogger(f'uvicorn.{__name__}')


@dataclass(frozen=True)
class Args:
    visit: Visit
    level: int
    i: int
    j: int


def run_transfer(task: TransferTask, send: Callable[[TransferTaskResponse], None]) -> None:
    def iter_tiles():
        for level, i, j in mergedtile_storage.iter_tiles(task.visit):
            yield Args(visit=task.visit, level=level, i=i, j=j)

    @throttle.throttle(0.1)
    def on_update(progress: TransferProgress):
        send(progress)

    with timeit(f'transfer enumerate {task.visit.id}'):
        params_list = list(iter_tiles())
        total = len(params_list)

    on_update(TransferProgress(transfer=Progress(count=0, total=total)))

    with timeit(f'transfer {task.visit.id}'):
        with ThreadPoolExecutor(2) as executor:
            futures = [executor.submit(process_tile, params) for params in params_list]
            for done, _ in enumerate(as_completed(futures)):
                progress = TransferProgress(transfer=Progress(count=done + 1, total=total))
                on_update(progress)
    throttle.flush(on_update)


def process_tile(args: Args) -> None:
    visit = args.visit
    level = args.level
    i = args.i
    j = args.j
    storage.put_quicklook_tile_bytes(visit, level, i, j, mergedtile_storage.get_tile_data(visit, level, i, j))
