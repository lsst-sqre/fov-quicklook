from dataclasses import dataclass, field
from typing import Any, Callable, List

from .window import Window


@dataclass
class WatcherManager:
    _w: Window
    members: List['Watcher'] = field(default_factory=list)

    def new(self, *, watch_on: Callable, on_change: Callable):
        watcher = Watcher(self, watch_on=watch_on, on_change=on_change, last_value=watch_on())
        self.members.append(watcher)
        return watcher

    def clear(self):
        while len(self.members) > 0:
            self.members.pop().unwatch()

    def _run_callbacks(self):
        for i, watcher in enumerate(self.members):
            try:
                new_value = watcher.watch_on()
                if new_value != watcher.last_value:
                    watcher.on_change()
                    watcher.last_value = new_value
            except Exception as e:  # pragma: no cover
                self._w.logger.warn(f'Error in watcher {i}:\n{e}')


@dataclass
class Watcher:
    manager: WatcherManager
    watch_on: Callable
    on_change: Callable
    last_value: Any

    def unwatch(self):
        try:
            self.manager.members.remove(self)
        except ValueError:  # pragma: no cover
            pass
