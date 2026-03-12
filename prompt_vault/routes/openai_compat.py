import logging
import time
import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session
from pydantic import BaseModel

from prompt_vault.database import get_session
from prompt_vault.models import PromptLogCreate
from prompt_vault.services.prompt_service import create_prompt_log
from prompt_vault.providers.registry import call_provider, ProviderError

logger = logging.getLogger("prompt_vault.routes.openai_compat")

router = APIRouter(tags=["openai-compat"])


def parse_model(model_str: str):
    """Parse 'provider/model' string. Bare model names default to openai."""
    if "/" in model_str:
        provider, model = model_str.split("/", 1)
        return provider, model
    return "openai", model_str


def messages_to_prompt(messages: list) -> str:
    """Convert OpenAI-style messages array to a single prompt string."""
    parts = []
    for msg in messages:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        if role == "system":
            parts.append(f"[System]: {content}")
        elif role == "assistant":
            parts.append(f"[Assistant]: {content}")
        else:
            parts.append(content)
    return "\n\n".join(parts)


# --- Request models ---

class ChatMessage(BaseModel):
    role: str
    content: str


class ChatCompletionRequest(BaseModel):
    model: str
    messages: List[ChatMessage]
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    stream: Optional[bool] = False


# --- Response models (OpenAI-compatible) ---

class ChatMessageResponse(BaseModel):
    role: str = "assistant"
    content: str


class Choice(BaseModel):
    index: int = 0
    message: ChatMessageResponse
    finish_reason: str = "stop"


class Usage(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class ChatCompletionResponse(BaseModel):
    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: List[Choice]
    usage: Usage


@router.post("/v1/chat/completions", response_model=ChatCompletionResponse)
def chat_completions(req: ChatCompletionRequest, session: Session = Depends(get_session)):
    if req.stream:
        from fastapi.responses import JSONResponse
        return JSONResponse(
            status_code=400,
            content={
                "error": {
                    "message": "Streaming is not supported by Prompt Vault",
                    "type": "invalid_request_error",
                    "code": "streaming_not_supported",
                }
            },
        )

    if not req.messages:
        from fastapi.responses import JSONResponse
        return JSONResponse(
            status_code=400,
            content={
                "error": {
                    "message": "messages must contain at least one message",
                    "type": "invalid_request_error",
                    "code": "invalid_messages",
                }
            },
        )

    provider, model = parse_model(req.model)
    prompt = messages_to_prompt([m.model_dump() for m in req.messages])

    try:
        result = call_provider(provider, model, prompt)
    except ProviderError as e:
        from fastapi.responses import JSONResponse
        return JSONResponse(
            status_code=e.status_code,
            content={
                "error": {
                    "message": str(e),
                    "type": "invalid_request_error" if e.status_code < 500 else "server_error",
                    "code": "model_error",
                }
            },
        )

    # Log with full token data
    tokens = result.tokens
    log_data = PromptLogCreate(
        prompt=prompt,
        response=result.response,
        model=model,
        provider=provider,
        latency_ms=result.latency_ms,
        status="success",
        prompt_tokens=tokens.get("prompt"),
        completion_tokens=tokens.get("completion"),
        total_tokens=tokens.get("total"),
    )
    create_prompt_log(session, log_data)

    return ChatCompletionResponse(
        id=f"chatcmpl-{uuid.uuid4().hex[:24]}",
        created=int(time.time()),
        model=req.model,
        choices=[
            Choice(
                message=ChatMessageResponse(content=result.response),
            )
        ],
        usage=Usage(
            prompt_tokens=tokens.get("prompt") or 0,
            completion_tokens=tokens.get("completion") or 0,
            total_tokens=tokens.get("total") or 0,
        ),
    )
