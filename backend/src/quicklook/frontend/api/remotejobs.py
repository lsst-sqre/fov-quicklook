import asyncio
import logging
import pickle
import traceback
from contextlib import asynccontextmanager
from functools import cache
from typing import Callable, TypeVar

import websockets

from quicklook.config import config
from quicklook.coordinator.quicklookjob.job import QuicklookJobReport
from quicklook.types import Visit
from quicklook.utils.asynctask import cancel_at_exit
from quicklook.utils.broadcastqueue import BroadcastQueue
from quicklook.utils.event import WatchEvent

T = TypeVar('T')
logger = logging.getLogger(f'uvicorn.{__name__}')


class _RemoteQuicklookJobsWatcher:

    def __init__(self):
        self._jobs: dict[Visit, QuicklookJobReport] = {}
        self._q = BroadcastQueue[dict[Visit, QuicklookJobReport]]()
        self._active = False

    @asynccontextmanager
    async def activate(self):
        self._active = True
        with cancel_at_exit(asyncio.create_task(self._watch())):
            try:
                yield
            finally:
                self._active = False

    async def _watch(self):
        while True:
            self._jobs = {}
            try:
                async with websockets.connect(f'{config.coordinator_ws_base_url}/quicklook-jobs/events.ws') as ws:
                    while True:
                        events: list[WatchEvent[QuicklookJobReport]] = pickle.loads(await ws.recv())  # type: ignore
                        for event in events:
                            match event.type:
                                case 'added':
                                    self._jobs[event.value.visit] = event.value
                                case 'deleted':
                                    self._jobs.pop(event.value.visit, None)
                                case 'modified':
                                    self._jobs[event.value.visit] = event.value
                                case _:  # pragma: no cover
                                    raise ValueError(f'unknown event type {event.type}')
                        self._q.put(self._jobs)
            except asyncio.CancelledError:
                break
            except Exception:  # pragma: no cover
                traceback.print_exc()
                logger.warning('retrying in 5 seconds')
                await asyncio.sleep(5)

    def subscribe(self):
        assert self._active
        return self._q.subscribe()

    async def watch(self, pick: Callable[[dict[Visit, QuicklookJobReport]], T]):
        v0 = pick(self._jobs)
        yield v0
        with self.subscribe() as sub:
            while True:
                v1: T = pick(await sub.get())
                if v0 is not v1:  # pragma: no branch
                    yield v1
                    v0 = v1

    @property
    def jobs(self):
        return self._jobs


@cache
def RemoteQuicklookJobsWatcher():
    return _RemoteQuicklookJobsWatcher()
