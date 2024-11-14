import asyncio
import logging
import pickle
import traceback
from contextlib import asynccontextmanager
from functools import cache
from typing import Callable, TypeVar

import websockets

from quicklook.config import config
from quicklook.coordinator.quicklook import Quicklook
from quicklook.types import Visit
from quicklook.utils.asynctask import cancel_at_exit
from quicklook.utils.broadcastqueue import BroadcastQueue
from quicklook.utils.event import WatchEvent

T = TypeVar('T')
logger = logging.getLogger(f'uvicorn.{__name__}')


class _RemoteQuicklookWatcher:
    def __init__(self):
        self._qls: dict[Visit, Quicklook] = {}
        self._q = BroadcastQueue[dict[Visit, Quicklook]]()
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
            self._qls = {}
            try:
                async with websockets.connect(f'{config.coordinator_ws_base_url}/quicklooks/*/events.ws') as ws:
                    while True:
                        events: list[WatchEvent[Quicklook]] = pickle.loads(await ws.recv())  # type: ignore
                        for event in events:
                            match event.type:
                                case 'added':
                                    self._qls[event.value.visit] = event.value
                                case 'deleted':
                                    self._qls.pop(event.value.visit, None)
                                case 'modified':
                                    self._qls[event.value.visit] = event.value
                        self._q.put(self._qls)
            except asyncio.CancelledError:
                break
            except:
                traceback.print_exc()
                logger.warning('retrying in 5 seconds')
                await asyncio.sleep(5)

    def subscribe(self):
        assert self._active
        return self._q.subscribe()

    async def watch(self, pick: Callable[[dict[Visit, Quicklook]], T]):
        v0 = pick(self._qls)
        yield v0
        with self.subscribe() as sub:
            while True:
                v1: T = pick(await sub.get())
                if v0 is not v1:
                    yield v1
                    v0 = v1

    @property
    def quicklooks(self):
        return self._qls


@cache
def RemoteQuicklookWather():
    return _RemoteQuicklookWatcher()


def remote_quicklook(visit: Visit) -> Quicklook | None:
    return RemoteQuicklookWather().quicklooks.get(visit)
