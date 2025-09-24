from dataclasses import dataclass, field
from typing import Literal
import uuid

from quicklook.types import Visit




@dataclass
class Job:
    visit: Visit
    id: str = field(default_factory=lambda: str(uuid.uuid4()))