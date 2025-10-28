import asyncio
import functools
from typing import Callable, TypeVar, ParamSpec

import quicklook.mylogging
from quicklook.comm.coordinator import shutdown_all_generators
from quicklook.config import config

logger = quicklook.mylogging.getLogger(__name__)

P = ParamSpec('P')
T = TypeVar('T')


class StageTimeoutError(Exception):
    pass


def with_timeout(func: Callable[P, T]) -> Callable[P, T]:
    @functools.wraps(func)
    async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
        try:
            result = await asyncio.wait_for(
                func(*args, **kwargs),
                timeout=config.pipeline_stage_timeout
            )
            return result
        except asyncio.TimeoutError:
            logger.error(f"Stage {func.__name__} timed out after {config.pipeline_stage_timeout} seconds")
            await shutdown_all_generators()
            raise StageTimeoutError(
                f"Stage {func.__name__} timed out after {config.pipeline_stage_timeout} seconds. "
                "All generators have been restarted."
            )
    
    return wrapper  # type: ignore
