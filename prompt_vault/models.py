from datetime import datetime, timezone
from typing import Optional

from sqlmodel import SQLModel, Field


class PromptLog(SQLModel, table=True):
    __tablename__ = "prompt_logs"

    id: Optional[int] = Field(default=None, primary_key=True)
    prompt: str
    response: str
    model: str
    provider: str
    latency_ms: float
    tags: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class PromptLogCreate(SQLModel):
    prompt: str
    response: str
    model: str
    provider: str
    latency_ms: float
    tags: Optional[str] = None
