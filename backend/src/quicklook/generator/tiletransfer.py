from typing import Callable
from quicklook.coordinator.quicklookjob.tasks import TransferTask
from quicklook.types import TransferTaskResponse


def run_transfer(task: TransferTask, send: Callable[[TransferTaskResponse], None]) -> None:
    pass
