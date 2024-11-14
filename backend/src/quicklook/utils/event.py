from dataclasses import dataclass, field
from typing import Generic, Literal, TypeVar

EventType = Literal['added', 'modified', 'deleted']
T = TypeVar('T')


@dataclass
class WatchEvent(Generic[T]):
    value: T
    type: EventType
