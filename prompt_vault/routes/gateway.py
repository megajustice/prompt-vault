from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session
from pydantic import BaseModel

from prompt_vault.database import get_session
from prompt_vault.models import PromptLogCreate
from prompt_vault.services.prompt_service import create_prompt_log
from prompt_vault.services.openai_provider import call_openai
from prompt_vault.services.anthropic_provider import call_anthropic

router = APIRouter(prefix="/api", tags=["gateway"])

PROVIDERS = {
    "openai": call_openai,
    "anthropic": call_anthropic,
}


class AskRequest(BaseModel):
    provider: str
    model: str
    prompt: str


class AskResponse(BaseModel):
    response: str
    provider: str
    model: str
    latency_ms: float


@router.post("/ask", response_model=AskResponse)
def ask(req: AskRequest, session: Session = Depends(get_session)):
    if req.provider not in PROVIDERS:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown provider '{req.provider}'. Supported: {list(PROVIDERS.keys())}",
        )

    call_fn = PROVIDERS[req.provider]

    try:
        result = call_fn(prompt=req.prompt, model=req.model)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e))

    # Log to database and JSON file using existing system
    log_data = PromptLogCreate(
        prompt=req.prompt,
        response=result["response"],
        model=result["model"],
        provider=result["provider"],
        latency_ms=result["latency_ms"],
    )
    create_prompt_log(session, log_data)

    return AskResponse(
        response=result["response"],
        provider=result["provider"],
        model=result["model"],
        latency_ms=result["latency_ms"],
    )
