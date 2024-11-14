from contextlib import contextmanager
from typing import Any, Generator, Generic, TypeVar

T = TypeVar('T')


class GlobalStack(Generic[T]):
    def __init__(self):
        self._stack: list[T] = []

    @contextmanager
    def push(self, value: T) -> Generator[T, None, None]:
        self._stack.append(value)
        try:
            yield value
        finally:
            self._stack.pop()

    def set_default(self, value: T) -> None:
        assert len(self._stack) == 0
        self._stack.append(value)

    @property
    def top(self) -> T:
        if len(self._stack) == 0:  # pragma: no cover
            raise ValueError('stack is empty')
        return self._stack[-1]
