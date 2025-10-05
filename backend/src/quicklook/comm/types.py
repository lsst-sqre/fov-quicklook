"""
Coordinator-Generator間の通信用型定義
"""

from dataclasses import dataclass
from functools import cached_property
from typing import NewType
from pydantic import BaseModel


GeneratorId = NewType("GeneratorId", str)


@dataclass(frozen=True)
class GeneratorInfo:
    id: GeneratorId
    host: str
    port: int

    @cached_property
    def url(self) -> str:
        return f"http://{self.host}:{self.port}"


class GeneratorRegistrationRequest(BaseModel):
    generator_id: GeneratorId
    port: int
