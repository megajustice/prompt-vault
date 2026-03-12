import csv
import io
import json
import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlmodel import Session
from pydantic import BaseModel

from prompt_vault.database import get_session
from prompt_vault.models import PromptLogCreate
from prompt_vault.services.prompt_service import (
    create_prompt_log,
    get_prompt_log,
    get_prompt_logs,
    update_tags,
)
from prompt_vault.providers.registry import call_provider, ProviderError, list_providers

logger = logging.getLogger("prompt_vault.routes.gateway")

router = APIRouter(prefix="/api", tags=["gateway"])


# --- Shared helper ---

def _log_result(session, prompt, result, tags=None, status="success", error_message=None, replay_of=None):
    """Log a provider result to the database and JSONL file."""
    tokens = result.tokens
    log_data = PromptLogCreate(
        prompt=prompt,
        response=result.response,
        model=result.model,
        provider=result.provider,
        latency_ms=result.latency_ms,
        tags=tags,
        status=status,
        error_message=error_message,
        prompt_tokens=tokens.get("prompt"),
        completion_tokens=tokens.get("completion"),
        total_tokens=tokens.get("total"),
        replay_of=replay_of,
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


# --- POST /api/replay ---

class ReplayRequest(BaseModel):
    log_id: int
    provider: Optional[str] = None
    model: Optional[str] = None


class ReplayResponse(BaseModel):
    response: str
    provider: str
    model: str
    latency_ms: float
    original_id: int
    new_id: int


@router.post("/replay", response_model=ReplayResponse)
def replay(req: ReplayRequest, session: Session = Depends(get_session)):
    original = get_prompt_log(session, req.log_id)
    if not original:
        raise HTTPException(status_code=404, detail="Original log not found")

    provider = req.provider or original.provider
    model = req.model or original.model

    try:
        result = call_provider(provider, model, original.prompt)
    except ProviderError as e:
        raise HTTPException(status_code=e.status_code, detail=str(e))

    entry = _log_result(
        session, original.prompt, result,
        tags="replay", replay_of=original.id,
    )

    return ReplayResponse(
        response=result.response,
        provider=result.provider,
        model=result.model,
        latency_ms=result.latency_ms,
        original_id=original.id,
        new_id=entry.id,
    )


# --- PATCH /api/logs/{log_id}/tags ---

class TagsUpdate(BaseModel):
    tags: str


@router.patch("/logs/{log_id}/tags")
def patch_tags(log_id: int, body: TagsUpdate, session: Session = Depends(get_session)):
    entry = update_tags(session, log_id, body.tags)
    if not entry:
        raise HTTPException(status_code=404, detail="Log not found")
    return {"id": entry.id, "tags": entry.tags}


# --- GET /api/export ---

@router.get("/export")
def export_logs(
    format: str = Query(default="json", pattern="^(json|csv|markdown)$"),
    limit: int = Query(default=200, le=1000),
    session: Session = Depends(get_session),
):
    logs = get_prompt_logs(session, limit=limit)

    if format == "csv":
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "id", "provider", "model", "prompt", "response",
            "latency_ms", "status", "tags", "prompt_tokens",
            "completion_tokens", "total_tokens", "created_at",
        ])
        for log in logs:
            writer.writerow([
                log.id, log.provider, log.model, log.prompt, log.response,
                log.latency_ms, log.status, log.tags or "",
                log.prompt_tokens or "", log.completion_tokens or "",
                log.total_tokens or "", log.created_at.isoformat(),
            ])
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=prompt_vault_export.csv"},
        )

    if format == "markdown":
        lines = ["# Prompt Vault Export\n"]
        for log in logs:
            lines.append(f"## Log #{log.id} — {log.provider}/{log.model}")
            lines.append(f"**Latency:** {log.latency_ms:.0f}ms | **Status:** {log.status} | **Date:** {log.created_at.isoformat()}")
            if log.tags:
                lines.append(f"**Tags:** {log.tags}")
            lines.append(f"\n### Prompt\n```\n{log.prompt}\n```")
            lines.append(f"\n### Response\n```\n{log.response}\n```\n---\n")
        content = "\n".join(lines)
        return StreamingResponse(
            iter([content]),
            media_type="text/markdown",
            headers={"Content-Disposition": "attachment; filename=prompt_vault_export.md"},
        )

    # JSON (default)
    data = []
    for log in logs:
        data.append({
            "id": log.id,
            "provider": log.provider,
            "model": log.model,
            "prompt": log.prompt,
            "response": log.response,
            "latency_ms": log.latency_ms,
            "status": log.status,
            "tags": log.tags,
            "prompt_tokens": log.prompt_tokens,
            "completion_tokens": log.completion_tokens,
            "total_tokens": log.total_tokens,
            "created_at": log.created_at.isoformat(),
        })
    content = json.dumps(data, indent=2)
    return StreamingResponse(
        iter([content]),
        media_type="application/json",
        headers={"Content-Disposition": "attachment; filename=prompt_vault_export.json"},
    )
