import uuid
from dataclasses import dataclass, field

from quicklook.types import Visit


@dataclass
class Job:
    visit: Visit
    id: str = field(default_factory=lambda: f'j-{uuid.uuid4().hex}')

    @classmethod
    def from_id(cls, id: str):
        return cls(id=id, visit=Visit(''))
