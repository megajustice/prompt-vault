import time
import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session
from pydantic import BaseModel

from prompt_vault.database import get_session
from prompt_vault.models import PromptLogCreate
from prompt_vault.services.prompt_service import create_prompt_log
from prompt_vault.services.openai_provider import call_openai
from prompt_vault.services.anthropic_provider import call_anthropic

router = APIRouter(tags=["openai-compat"])

PROVIDERS = {
    "openai": call_openai,
    "anthropic": call_anthropic,
}

# Models that don't need a prefix are assumed OpenAI
OPENAI_MODELS = {"gpt-4o", "gpt-4o-mini", "gpt-4", "gpt-4-turbo", "gpt-3.5-turbo"}


def parse_model(model_str: str):
    """Parse 'provider/model' string. Bare model names default to openai."""
    if "/" in model_str:
        provider, model = model_str.split("/", 1)
        return provider, model
    if model_str in OPENAI_MODELS or model_str.startswith("gpt-"):
        return "openai", model_str
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
        raise HTTPException(status_code=400, detail="Streaming is not supported")

    provider, model = parse_model(req.model)

    if provider not in PROVIDERS:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown provider '{provider}'. Use format: provider/model (e.g. anthropic/claude-sonnet-4-6)",
        )

    prompt = messages_to_prompt([m.dict() for m in req.messages])
    call_fn = PROVIDERS[provider]

    try:
        result = call_fn(prompt=prompt, model=model)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e))

    # Log using existing system
    log_data = PromptLogCreate(
        prompt=prompt,
        response=result["response"],
        model=model,
        provider=provider,
        latency_ms=result["latency_ms"],
    )
    create_prompt_log(session, log_data)

    tokens = result.get("tokens", {})

    return ChatCompletionResponse(
        id=f"chatcmpl-{uuid.uuid4().hex[:24]}",
        created=int(time.time()),
        model=req.model,
        choices=[
            Choice(
                message=ChatMessageResponse(content=result["response"]),
            )
        ],
        usage=Usage(
            prompt_tokens=tokens.get("prompt") or 0,
            completion_tokens=tokens.get("completion") or 0,
            total_tokens=tokens.get("total") or 0,
        ),
    )
