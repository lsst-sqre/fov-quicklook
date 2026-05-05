import abc
import json
from typing import Any, Callable, TypeVar, cast, Optional


class CommBase(abc.ABC):
    @abc.abstractmethod
    def on_msg(self, callback: Callable):  # pragma: no cover
        ...

    @abc.abstractmethod
    def send(self, msg: Any):  # pragma: no cover
        ...

    @abc.abstractmethod
    def wait_for_query_response_text(self, query_id: str) -> Any:  # pragma: no cover
        ...

    def wait_for_response(self, query_id: str) -> Any:
        text = self.wait_for_query_response_text(query_id)
        return json.loads(text)

    def close(self):
        pass


T = TypeVar('T')


def remove_none(o: T) -> T:
    if isinstance(o, dict):
        return cast(T, {k: remove_none(v) for k, v in o.items() if not v is None})
    if isinstance(o, list):
        return cast(T, [remove_none(e) for e in o])
    return o
