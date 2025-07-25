import logging
import multiprocessing
import os
import signal
from contextlib import contextmanager
from dataclasses import dataclass
from multiprocessing.connection import Connection
from typing import Callable

logger = logging.getLogger(f'uvicorn.{__name__}')

# Cannot use multiprocessing.Pool directly within Uvicorn.
# A child process is launched using multiprocessing.Process,
# where multiprocessing.Pool can be used.
# The child process and parent process communicate via multiprocessing.Pipe.


@dataclass(frozen=True)
class ProcessHandle:
    comm: Connection
    process: multiprocessing.Process

    def sigint(self):
        assert self.process.pid
        os.kill(self.process.pid, signal.SIGINT)
        self.process.join()


@contextmanager
def spawn_process_with_comm(process_target: Callable[[Connection], None]):
    comm, child_comm = multiprocessing.Pipe()
    worker_process = multiprocessing.Process(target=process_target, args=(child_comm,))
    worker_process.start()
    try:
        yield ProcessHandle(comm, worker_process)
    finally:
        comm.close()
        try:
            worker_process.join()
        except:
            # この行はデバッグ用
            # 本当はこのtry/exceptは必要ない・・はず・・
            logger.exception('Failed to join process')
