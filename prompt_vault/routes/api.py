from fastapi import APIRouter, Depends, Query
from sqlmodel import Session

from prompt_vault.database import get_session
from prompt_vault.models import PromptLog, PromptLogCreate
from prompt_vault.services.prompt_service import (
    create_prompt_log,
    get_prompt_log,
    get_prompt_logs,
    search_prompt_logs,
)

router = APIRouter(prefix="/api", tags=["api"])


@router.post("/logs", response_model=PromptLog, status_code=201)
def log_prompt(data: PromptLogCreate, session: Session = Depends(get_session)):
    return create_prompt_log(session, data)


@router.get("/logs", response_model=list[PromptLog])
def list_logs(
    skip: int = 0,
    limit: int = Query(default=50, le=200),
    session: Session = Depends(get_session),
):
    return get_prompt_logs(session, skip=skip, limit=limit)


@router.get("/logs/search", response_model=list[PromptLog])
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
