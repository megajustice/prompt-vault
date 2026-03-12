from typing import Optional

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session

from prompt_vault.database import get_session
from prompt_vault.services.prompt_service import (
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
from prompt_vault.providers.registry import list_providers
from prompt_vault.providers.base import KNOWN_MODELS

templates = Jinja2Templates(directory="prompt_vault/templates")

router = APIRouter(tags=["ui"])


@router.get("/", response_class=HTMLResponse)
def dashboard(request: Request, session: Session = Depends(get_session)):
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "total": get_total_count(session),
        "providers": get_provider_breakdown(session),
        "models": get_model_breakdown(session),
        "latency_by_provider": get_avg_latency_by_provider(session),
        "latency_by_model": get_avg_latency_by_model(session),
        "status_breakdown": get_status_breakdown(session),
        "daily_volume": get_daily_volume(session),
        "tokens": get_token_totals(session),
        "recent": get_prompt_logs(session, limit=10),
    })


@router.get("/prompts", response_class=HTMLResponse)
def prompts_list(
    request: Request,
    provider: Optional[str] = None,
    model: Optional[str] = None,
    status: Optional[str] = None,
    tag: Optional[str] = None,
    q: str = Query(default=""),
    page: int = Query(default=1, ge=1),
    session: Session = Depends(get_session),
):
    per_page = 50
    skip = (page - 1) * per_page

    if q:
        logs = search_prompt_logs(session, query=q, limit=per_page)
    else:
        logs = get_prompt_logs(
            session, skip=skip, limit=per_page,
            provider=provider, model=model, status=status, tag=tag,
        )

    ctx = {
        "request": request,
        "logs": logs,
        "query": q,
        "page": page,
        "provider_filter": provider or "",
        "model_filter": model or "",
        "status_filter": status or "",
        "tag_filter": tag or "",
        "providers": get_distinct_providers(session),
        "models": get_distinct_models(session),
    }

    if request.headers.get("HX-Request"):
        return templates.TemplateResponse("partials/prompt_list.html", ctx)
    return templates.TemplateResponse("prompts.html", ctx)


@router.get("/prompts/{log_id}", response_class=HTMLResponse)
def detail(log_id: int, request: Request, session: Session = Depends(get_session)):
    entry = get_prompt_log(session, log_id)
    if not entry:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Log not found")

    replay_chain = get_prompt_logs(session, limit=100)
    replay_chain = [r for r in replay_chain if r.replay_of == log_id]

    return templates.TemplateResponse("detail.html", {
        "request": request,
        "entry": entry,
        "replay_chain": replay_chain,
        "available_providers": list_providers(),
        "known_models": KNOWN_MODELS,
    })


@router.get("/compare", response_class=HTMLResponse)
def compare_page(request: Request):
    providers = list_providers()
    return templates.TemplateResponse("compare.html", {
        "request": request,
        "providers": providers,
        "known_models": KNOWN_MODELS,
    })


@router.get("/stats", response_class=HTMLResponse)
def stats_page(request: Request, session: Session = Depends(get_session)):
    return templates.TemplateResponse("stats.html", {
        "request": request,
        "total": get_total_count(session),
        "providers": get_provider_breakdown(session),
        "models": get_model_breakdown(session),
        "latency_by_provider": get_avg_latency_by_provider(session),
        "latency_by_model": get_avg_latency_by_model(session),
        "status_breakdown": get_status_breakdown(session),
        "daily_volume": get_daily_volume(session),
        "tokens": get_token_totals(session),
    })


# Legacy redirects
@router.get("/logs/{log_id}", response_class=HTMLResponse)
def detail_legacy(log_id: int, request: Request):
    return RedirectResponse(f"/prompts/{log_id}", status_code=301)


@router.get("/search", response_class=HTMLResponse)
def search_legacy(request: Request, q: str = Query(default="")):
    return RedirectResponse(f"/prompts?q={q}", status_code=301)
