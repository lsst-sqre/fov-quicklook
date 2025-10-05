from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Literal

from quicklook.comm.types import GeneratorId
from quicklook.job.job import Job
from quicklook.types import CcdName, Progress

JobStage = Literal['queued', 'generate_single_fits_tiles', 'merge_tiles', 'transfer_tiles', 'done']



@dataclass
class JobStatus:
    # coordinator内で使用される
    job: Job

    stage: JobStage = 'queued'
    generate_single_fits_tiles: dict[CcdName, Progress] = field(default_factory=dict)
    merge_tiles: dict[GeneratorId, Progress] = field(default_factory=dict)
    transfer_tiles: dict[GeneratorId, Progress] = field(default_factory=dict)

    _watchers: list['_Watcher'] = field(default_factory=list)

    @classmethod
    def from_job(cls, job: Job) -> 'JobStatus':
        return cls(job)

    @asynccontextmanager
    async def watch(self):
        before = [w.which(self) for w in self._watchers]
        yield self
        after = [w.which(self) for w in self._watchers]
        for w, b, a in zip(self._watchers, before, after):
            if b != a:
                await w.cb(self.job)

    def on_change(
        self,
        cb: Callable[[Job], Awaitable],
        which: Callable[['JobStatus'], Any] | None = None,
    ):
        which = which or (lambda _: object())
        self._watchers.append(_Watcher(cb, which))


@dataclass
class _Watcher:
    cb: Callable[[Job], Awaitable]
    which: Callable[['JobStatus'], Any]
