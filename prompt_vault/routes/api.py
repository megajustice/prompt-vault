from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlmodel import Session

from prompt_vault.database import get_session
from prompt_vault.models import PromptLog, PromptLogCreate
from prompt_vault.services.prompt_service import (
    create_prompt_log,
    get_prompt_log,
    get_prompt_logs,
    search_prompt_logs,
    get_total_count,
    get_provider_breakdown,
    get_model_breakdown,
    get_avg_latency_by_provider,
    get_avg_latency_by_model,
    get_status_breakdown,
    get_daily_volume,
    get_token_totals,
    get_distinct_providers,
    get_distinct_models,
)
from prompt_vault.providers.base import KNOWN_MODELS
from prompt_vault.providers.registry import refresh_lmstudio_models

router = APIRouter(prefix="/api", tags=["api"])


@router.post("/logs", response_model=PromptLog, status_code=201)
def log_prompt(data: PromptLogCreate, session: Session = Depends(get_session)):
    return create_prompt_log(session, data)


@router.get("/logs", response_model=List[PromptLog])
def list_logs(
    skip: int = 0,
    limit: int = Query(default=50, le=200),
    provider: Optional[str] = None,
    model: Optional[str] = None,
    status: Optional[str] = None,
    tag: Optional[str] = None,
    session: Session = Depends(get_session),
):
    return get_prompt_logs(
        session, skip=skip, limit=limit,
        provider=provider, model=model, status=status, tag=tag,
    )


@router.get("/logs/search", response_model=List[PromptLog])
def search_logs(
    q: str = Query(min_length=1),
    limit: int = Query(default=50, le=200),
    session: Session = Depends(get_session),
):
    return search_prompt_logs(session, query=q, limit=limit)


@router.get("/logs/{log_id}", response_model=PromptLog)
def get_log(log_id: int, session: Session = Depends(get_session)):
    entry = get_prompt_log(session, log_id)
    if not entry:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Log not found")
    return entry


@router.get("/stats")
def get_stats(session: Session = Depends(get_session)):
    return {
        "total_prompts": get_total_count(session),
        "providers": get_provider_breakdown(session),
        "models": get_model_breakdown(session),
        "avg_latency_by_provider": get_avg_latency_by_provider(session),
        "avg_latency_by_model": get_avg_latency_by_model(session),
        "status_breakdown": get_status_breakdown(session),
        "daily_volume": get_daily_volume(session),
        "token_totals": get_token_totals(session),
    }


@router.get("/filters")
def get_filters(session: Session = Depends(get_session)):
    return {
        "providers": get_distinct_providers(session),
        "models": get_distinct_models(session),
    }


@router.get("/models")
def get_models():
    """Return all known models, including auto-discovered LM Studio models."""
    refresh_lmstudio_models()
    return KNOWN_MODELS


@router.post("/models/refresh")
def refresh_models():
    """Force re-discovery of LM Studio models."""
    refresh_lmstudio_models()
    lm_models = KNOWN_MODELS.get("lmstudio", [])
    return {
        "lmstudio_available": len(lm_models) > 0,
        "lmstudio_models": lm_models,
        "all_models": KNOWN_MODELS,
    }
