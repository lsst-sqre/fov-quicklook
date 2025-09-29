import time
from typing import Callable, TypeVar

F = TypeVar('F')
empty = object()


def throttle(interval: float) -> Callable[[F], F]:
    def decorator(f: F) -> F:
        last_invoke = 0
        last_args = empty

        def throttled(*args, **kwargs):
            nonlocal last_invoke, last_args
            now = time.time()
            last_args = args, kwargs
            if now - last_invoke > interval:
                last_args = empty
                last_invoke = now
                return f(*args, **kwargs)  # type: ignore

        def flush():
            nonlocal last_args, last_invoke
            if last_args is not empty:
                last_invoke = time.time()
                try:
                    f(*last_args[0], **last_args[1])  # type: ignore
                finally:
                    last_args = empty

        throttled.flush = flush  # type: ignore

        return throttled  # type: ignore

    return decorator


def flush(f: Callable):
    f.flush()  # type: ignore
