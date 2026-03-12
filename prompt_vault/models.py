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
    status: str = Field(default="success")
    error_message: Optional[str] = None
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    total_tokens: Optional[int] = None
    replay_of: Optional[int] = Field(default=None)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class PromptLogCreate(SQLModel):
    prompt: str
    response: str
    model: str
    provider: str
    latency_ms: float
    tags: Optional[str] = None
    status: str = "success"
    error_message: Optional[str] = None
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    total_tokens: Optional[int] = None
    replay_of: Optional[int] = None
