import time
from typing import Callable, TypeVar

R = TypeVar('R')


def retry_on_error[R](
    f: Callable[..., R],
    expected: type[Exception],
    n_retry=10,
    wait=0.05,
) -> R:
    for _ in range(1, n_retry):
        try:
            return f()
        except expected:  # pragma: no cover
            time.sleep(wait)
            wait *= 1.5
            continue
    return f()  # pragma: no cover
