from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable

from quicklook.job.job import Job
from quicklook.job.status import JobStatus


@dataclass
class JobWatcher:
    job: Job
    _watchers: list['_Watcher'] = field(default_factory=list)

    @classmethod
    def from_job(cls, job: Job) -> 'JobWatcher':
        return cls(job=job)

    @asynccontextmanager
    async def watch_status(self):
        before = [w.which(self.job.status) for w in self._watchers]
        yield self
        after = [w.which(self.job.status) for w in self._watchers]
        for w, b, a in zip(self._watchers, before, after):
            if b != a:  # pragma: no branch
                await w.cb(self.job)

    def on_change_status(
        self,
        cb: Callable[[Job], Awaitable],
        which: Callable[[JobStatus], Any] | None = None,
    ):
        which = which or (lambda _: object())
        self._watchers.append(_Watcher(cb, which))


@dataclass
class _Watcher:
    cb: Callable[[Job], Awaitable]
    which: Callable[[JobStatus], Any]
