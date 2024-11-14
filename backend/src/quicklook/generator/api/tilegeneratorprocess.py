import logging
import multiprocessing
import threading
import traceback
from multiprocessing.connection import Connection
from typing import Callable

from quicklook.coordinator.tasks import GeneratorTask
from quicklook.generator.progress import GeneratorProgress, GeneratorProgressReporter
from quicklook.generator.tasks import run_generator
from quicklook.types import GeneratorResult, MessageFromGeneratorToCoordinator
from quicklook.utils import throttle
from quicklook.utils.timeit import timeit

logger = logging.getLogger('uvicorn')


class TileGeneratorProcess:
    # uvicorn内ではmultiprocessing.Poolが使えないので別プロセスで処理を行う
    def __init__(self):
        pass

    def __enter__(self):
        self._comm, child_comm = multiprocessing.Pipe()
        self._server = multiprocessing.Process(target=process, args=(child_comm,))
        self._server.start()
        self._lock = threading.Lock()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._comm.send(None)
        self._comm.close()
        self._server.join()

    def create_quicklook(
        self,
        task: GeneratorTask,
        *,
        on_update: Callable[[MessageFromGeneratorToCoordinator], None],
    ):
        with self._lock:
            logger.info(f'Create quicklook for {task}')
            with timeit(f'create_quicklook {task}'):
                self._comm.send(task)
                while True:
                    progress: GeneratorProgress = self._comm.recv()
                    if progress is None:
                        break
                    on_update(progress)
            on_update(None)
            logger.info(f'Finished quicklook for {task}')


def process(comm: Connection):

    @throttle.throttle(0.1)
    def on_update(progress: GeneratorProgress):
        comm.send(progress)

    try:
        while True:
            task: GeneratorTask | None = comm.recv()
            if task is None:
                break
            try:
                result = run_generator(task, on_update)
                throttle.flush(on_update)
                comm.send(GeneratorResult(result))
            except Exception as e:  # pragma: no cover
                traceback.print_exc()
                comm.send(e)
            finally:
                comm.send(None)
    finally:
        comm.close()
