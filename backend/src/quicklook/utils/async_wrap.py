import asyncio
from typing import Any, Callable


class async_wrap:
    """sync メソッドから asyncio.to_thread ラッパーを自動生成するディスクリプタ。

    使い方:
        class MyClass:
            def get_data_sync(self, key: str) -> bytes:
                ...

            get_data = async_wrap(get_data_sync)
    """

    def __init__(self, sync_fn: Callable[..., Any]):
        self._name = sync_fn.__name__.removesuffix('_sync')
        self._sync_attr = sync_fn.__name__

    def __set_name__(self, owner: type, name: str) -> None:
        self._name = name

    def __get__(self, obj: Any, objtype: type | None = None) -> Callable[..., Any]:
        if obj is None:
            return self  # type: ignore
        sync_method = getattr(obj, self._sync_attr)

        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            return await asyncio.to_thread(sync_method, *args, **kwargs)

        wrapper.__name__ = self._name
        wrapper.__qualname__ = f'{type(obj).__qualname__}.{self._name}'
        return wrapper
