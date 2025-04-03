import contextlib
import multiprocessing
import queue
import threading
from dataclasses import dataclass
from functools import cached_property
from typing import Any, Callable

import tqdm

from quicklook.coordinator.quicklookjob.tasks import GenerateTask
from quicklook.types import GenerateProgress, GenerateTaskResponse, Progress
from quicklook.utils.exitstack import exit_stack


class GeneratorProgressReporter:
    # これいる？
    # 大袈裟すぎる気が。
    def __init__(
        self,
        task: GenerateTask,
        *,
        on_update: Callable[[GenerateProgress], None] | None = None,
    ):
        self._task = task
        self._on_update = on_update
        self._progress = GenerateProgress(
            download=Progress(0, len(task.ccd_names)),
            preprocess=Progress(0, len(task.ccd_names)),
            maketile=Progress(0, 0),
        )
        self._refresh()

    def __enter__(self):
        with exit_stack() as self._exit_stack:
            self._exit_stack = contextlib.ExitStack()
            manager = multiprocessing.Manager()
            self._exit_stack.enter_context(manager)
            self._q = manager.Queue()
            self._exit_stack.enter_context(self._watch())
            return self

    def __exit__(self, exc_type, exc_value, traceback):
        self._exit_stack.close()

    @contextlib.contextmanager
    def _watch(self):
        t = threading.Thread(target=self._watch_thread)
        t.start()
        try:
            yield
        finally:
            self._q.put(None)
            t.join()

    def _watch_thread(self):
        while True:
            msg = self._q.get()
            match msg:
                case None:
                    break
                case PreprocessDoneMsg():
                    self._progress.preprocess.count += 1
                    self._refresh()
                case UpdateMaketileProgressMsg():
                    self._update_maketile_progress(msg)
                case _:  # pragma: no cover
                    raise ValueError(f'Unknown message: {msg}')

    @cached_property
    def _maketiles_progress_dict(self):
        return ProgressDict(len(self._task.ccd_names))

    def _update_maketile_progress(self, msg: 'UpdateMaketileProgressMsg'):
        self._progress.maketile = self._maketiles_progress_dict.update(msg.ccd_name, msg.progress).merged()
        self._refresh()

    def _refresh(self):
        if self._on_update:  # pragma: no branch
            self._on_update(self._progress)

    def download_done(self):
        self._progress.download.count += 1
        self._refresh()

    @cached_property
    def updator(self):
        return GeneratorProgressReporter.InterProcessUpdator(self._q)

    @dataclass
    class InterProcessUpdator:
        _q: queue.Queue

        def preprocess_done(self):
            self._q.put(PreprocessDoneMsg())

        def update_maketile_progress(self, ccd_name: str, progress: Progress):
            self._q.put(UpdateMaketileProgressMsg(ccd_name, progress))


class PreprocessDoneMsg:
    pass


@dataclass
class UpdateMaketileProgressMsg:
    ccd_name: str
    progress: Progress


class ProgressDict:
    def __init__(self, max_size=1):
        self._max_sizae = max_size
        self.d: dict[str, Progress] = {}

    def update(self, pod_name: str, progress: Progress):
        self.d[pod_name] = progress
        return self

    def merged(self):
        p = Progress(
            count=sum(p.count for p in self.d.values()),
            total=sum(p.total for p in self.d.values()),
        )
        # keyが増えたときにcount/totalが急に減らないように。
        active = len(self.d)
        p.count *= active
        p.total *= self._max_sizae
        return p


@contextlib.contextmanager
def tqdm_progres_bar():
    stack = contextlib.ExitStack()
    bars = [
        tqdm.tqdm(desc='Downloads', total=0),
        tqdm.tqdm(desc='Preprocess', total=0),
        tqdm.tqdm(desc='Make Tiles', total=0),
    ]
    for bar in bars:
        stack.enter_context(bar)

    def on_update(progress: GenerateTaskResponse):
        if not isinstance(progress, GenerateProgress):
            return

        for bar, p in zip(
            bars,
            [
                progress.download,
                progress.preprocess,
                progress.maketile,
            ],
        ):
            if p.total != bar.total or p.count != bar.n:
                bar.total = p.total
                bar.n = p.count
                bar.refresh()

    try:
        yield on_update
    finally:
        stack.close()
