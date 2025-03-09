import logging
from typing import Any, Callable, TypeVar

from quicklook.coordinator.quicklookjob.tasks import GenerateTask
from quicklook.generator.api import tile_transfer_process_target
from quicklook.generator.api.baseprocesshandler import BaseProcessHandler
from quicklook.generator.progress import GenerateProgress
from quicklook.types import GenerateTaskResponse
from quicklook.utils.timeit import timeit

logger = logging.getLogger(f'uvicorn.{__name__}')


def create_tile_generate_process() -> BaseProcessHandler[GenerateTask, GenerateProgress]:
    return BaseProcessHandler[GenerateTask, GenerateProgress](process_target=tile_transfer_process_target)
