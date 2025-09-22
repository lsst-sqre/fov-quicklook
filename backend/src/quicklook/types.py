from dataclasses import dataclass
from functools import cache


@dataclass(frozen=True)
class Visit:
    id: str  # '{data_type}:{exposure}'

    @cache
    def _parts(self):
        return self.id.split(':')

    @property
    def data_type(self):
        return self._parts()[-2]

    @property
    def name(self):
        return self._parts()[-1]

    @classmethod
    def from_id(cls, id: str):
        return cls(id)
