"""
Coordinator-Generator間の通信用型定義
"""

from dataclasses import dataclass
from pydantic import BaseModel


@dataclass
class GeneratorInfo:
    host: str
    port: int
    max_concurrent_jobs: int

    @property
    def url(self) -> str:
        return f"http://{self.host}:{self.port}"


class GeneratorRegistrationRequest(BaseModel):
    port: int
    max_concurrent_jobs: int
