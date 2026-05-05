from dataclasses import dataclass, field
from typing import List, Literal

from .window import Window

LogLevel = Literal['debug', 'info', 'log', 'warn']


@dataclass
class Logger:
    _w: Window
    max_length: int = 100
    buffer: List[str] = field(default_factory=list)

    def _log(self, msg: str, level: LogLevel = 'info', js_alert: bool = False, js_console: bool = True):
        self.buffer.append(msg)
        while len(self.buffer) > self.max_length:
            self.buffer.pop(0)
        if js_alert:  # pragma: no cover
            self._w.show_error(title=level, body=msg)
        if js_console:  # pragma: no cover
            self._w.js_console(level, msg)

    def info(self, msg: str, js_alert: bool = False, js_console: bool = True):
        self._log(msg, 'info', js_alert, js_console)

    def warn(self, msg: str, js_alert: bool = True, js_console: bool = True):
        self._log(msg, 'warn', js_alert, js_console)
