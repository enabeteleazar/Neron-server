from pydantic import BaseModel
from typing import Optional, Dict, Any


class LLMRequest(BaseModel):
    message: str
    task: Optional[str] = "default"
    provider: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
