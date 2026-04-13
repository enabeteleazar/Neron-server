from pydantic import BaseModel


class LLMRequest(BaseModel):
    message: str
    task: str | None = None
