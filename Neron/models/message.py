from dataclasses import dataclass
from typing import Optional

@dataclass
class NeronMessage:
    source: str
    target: str
    content: str
    metadata: Optional[dict] = None