import functools
import time
from typing import Any, Callable, TypeVar, ParamSpec, cast

T = TypeVar('T')
P = ParamSpec('P')


def ttlcache(ttl: float | None = None) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """
    A decorator that caches function results with a configurable TTL (Time-To-Live).

    Similar to functools.cache, but with an added TTL feature.

    Args:
        ttl: Time-to-live in seconds for cache entries. None means entries never expire.

    Returns:
        A decorator function
    """

    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        cache: dict[Any, tuple[T, float]] = {}

        @functools.wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            key = (args, frozenset(kwargs.items()))

            current_time = time.time()
            if key in cache:
                result, timestamp = cache[key]
                if ttl is None or current_time - timestamp < ttl:
                    return result

            result = func(*args, **kwargs)
            cache[key] = (result, current_time)
            return result

        def cache_clear() -> None:
            """Clear the cache and statistics."""
            cache.clear()

        def cache_info() -> dict[str, Any]:
            """Return cache information."""
            return {"currsize": len(cache), "ttl": ttl}

        wrapper.cache_clear = cache_clear  # type: ignore
        wrapper.cache_info = cache_info  # type: ignore

        return cast(Callable[P, T], wrapper)

    # Handle case when decorator is used without arguments
    if callable(ttl):  # type: ignore
        func, ttl = ttl, None
        return decorator(func)  # type: ignore

    return decorator
