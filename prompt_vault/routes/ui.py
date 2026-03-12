from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session

from prompt_vault.database import get_session
from prompt_vault.services.prompt_service import (
    get_prompt_log,
    get_prompt_logs,
    search_prompt_logs,
)

templates = Jinja2Templates(directory="prompt_vault/templates")

router = APIRouter(tags=["ui"])


@router.get("/", response_class=HTMLResponse)
def index(request: Request, session: Session = Depends(get_session)):
    logs = get_prompt_logs(session)
    return templates.TemplateResponse(
        "index.html", {"request": request, "logs": logs}
    )


@router.get("/logs/{log_id}", response_class=HTMLResponse)
def detail(log_id: int, request: Request, session: Session = Depends(get_session)):
    entry = get_prompt_log(session, log_id)
    if not entry:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Log not found")
    return templates.TemplateResponse(
        "detail.html", {"request": request, "entry": entry}
    )


@router.get("/search", response_class=HTMLResponse)
def search(
    request: Request,
    q: str = Query(default=""),
    session: Session = Depends(get_session),
):
    if q:
        logs = search_prompt_logs(session, query=q)
    else:
        logs = get_prompt_logs(session)
    # HTMX partial response
    if request.headers.get("HX-Request"):
        return templates.TemplateResponse(
            "partials/prompt_list.html", {"request": request, "logs": logs}
        )
    return templates.TemplateResponse(
        "index.html", {"request": request, "logs": logs, "query": q}
    )
