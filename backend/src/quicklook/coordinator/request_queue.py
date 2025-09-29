import asyncio
import itertools
from dataclasses import dataclass
from typing import Awaitable, Callable

from quicklook.types import VisitName


@dataclass
class _QuicklookRequest:
    visit: VisitName
    vote: int
    seq: int

    def sort_key(self):
        return -self.vote, self.seq


class QuicklookRequestQueue:
    '''
    voteの小さい順, 同じvoteの場合は先にリクエストされた順に処理する
    '''

    def __init__(
        self,
        process_request: Callable[[_QuicklookRequest], Awaitable[None]],
    ):
        self._requests: dict[VisitName, _QuicklookRequest] = {}
        self._push_event = asyncio.Event()
        self._seq = itertools.count()
        self._process_request = process_request

    def push(self, visit: VisitName):
        req = _QuicklookRequest(visit=visit, vote=0, seq=next(self._seq))
        if req.visit in self._requests:
            self._requests[req.visit] = req
            self._push_event.set()

    async def _pop(self) -> _QuicklookRequest:
        await self._push_event.wait()
        self._push_event.clear()
        assert len(self._requests) > 0
        top = sorted(self._requests.values(), key=_QuicklookRequest.sort_key)[0]
        del self._requests[top.visit]
        return top

    async def main_loop(self):
        while True:
            req = await self._pop()
            await self._process_request(req)
