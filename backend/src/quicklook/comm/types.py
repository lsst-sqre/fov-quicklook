"""
Coordinator-Generator間の通信用型定義
"""

from dataclasses import dataclass
from functools import cached_property
from pydantic import BaseModel


@dataclass(frozen=True)
class GeneratorInfo:
    id: str
    host: str
    port: int

    @cached_property
    def url(self) -> str:
        return f"http://{self.host}:{self.port}"


class GeneratorRegistrationRequest(BaseModel):
    generator_id: str
    port: int
