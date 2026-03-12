import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session
from pydantic import BaseModel

from prompt_vault.database import get_session
from prompt_vault.models import PromptLogCreate
from prompt_vault.services.prompt_service import create_prompt_log
from prompt_vault.providers.registry import call_provider, ProviderError, list_providers

logger = logging.getLogger("prompt_vault.routes.gateway")

router = APIRouter(prefix="/api", tags=["gateway"])


# --- Shared helper ---

def _log_result(session, prompt, result, tags=None):
    """Log a provider result to the database and JSONL file."""
    log_data = PromptLogCreate(
        prompt=prompt,
        response=result.response,
        model=result.model,
        provider=result.provider,
        latency_ms=result.latency_ms,
        tags=tags,
    )
    return create_prompt_log(session, log_data)


# --- POST /api/ask ---

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
    try:
        result = call_provider(req.provider, req.model, req.prompt)
    except ProviderError as e:
        raise HTTPException(status_code=e.status_code, detail=str(e))

    _log_result(session, req.prompt, result)

    return AskResponse(
        response=result.response,
        provider=result.provider,
        model=result.model,
        latency_ms=result.latency_ms,
    )


# --- POST /api/compare ---

class ModelTarget(BaseModel):
    provider: str
    model: str


class CompareRequest(BaseModel):
    prompt: str
    models: List[ModelTarget]


class CompareResult(BaseModel):
    response: str
    provider: str
    model: str
    latency_ms: float
    error: Optional[str] = None


class CompareResponse(BaseModel):
    prompt: str
    results: List[CompareResult]


@router.post("/compare", response_model=CompareResponse)
def compare(req: CompareRequest, session: Session = Depends(get_session)):
    if not req.models:
        raise HTTPException(status_code=400, detail="At least one model is required")

    results = []
    for target in req.models:
        try:
            result = call_provider(target.provider, target.model, req.prompt)
        except ProviderError as e:
            logger.warning("Compare target %s/%s failed: %s", target.provider, target.model, e)
            results.append(CompareResult(
                response="",
                provider=target.provider,
                model=target.model,
                latency_ms=0,
                error=str(e),
            ))
            continue

        _log_result(session, req.prompt, result, tags="compare")

        results.append(CompareResult(
            response=result.response,
            provider=result.provider,
            model=result.model,
            latency_ms=result.latency_ms,
        ))

    return CompareResponse(prompt=req.prompt, results=results)
