"""
Coordinator-Generator間の通信用型定義
"""

from dataclasses import dataclass
from functools import cached_property
from typing import NewType
from pydantic import BaseModel


GeneratorId = NewType("GeneratorId", str)
CoordinatorId = NewType("CoordinatorId", str)


@dataclass(frozen=True)
class GeneratorInfo:
    id: GeneratorId
    host: str
    port: int

    @cached_property
    def url(self) -> str:
        return f"http://{self.host}:{self.port}"

    @cached_property
    def ws_url(self) -> str:
        assert self.url.startswith("http://")
        return "ws://" + self.url[7:]


class GeneratorRegistrationRequest(BaseModel):
    generator_id: GeneratorId
    port: int
    coordinator_id: CoordinatorId | None = None


class GeneratorRegistrationResponse(BaseModel):
    coordinator_id: CoordinatorId
