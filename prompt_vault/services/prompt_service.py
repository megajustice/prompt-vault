from typing import Optional

from sqlmodel import Session, select, col

from prompt_vault.models import PromptLog, PromptLogCreate
from prompt_vault.services.json_logger import write_log_entry


def create_prompt_log(session: Session, data: PromptLogCreate) -> PromptLog:
    entry = PromptLog.model_validate(data)
    session.add(entry)
    session.commit()
    session.refresh(entry)
    write_log_entry(entry)
    return entry


def get_prompt_logs(
    session: Session, skip: int = 0, limit: int = 50
) -> list[PromptLog]:
    statement = (
        select(PromptLog)
        .order_by(col(PromptLog.created_at).desc())
        .offset(skip)
        .limit(limit)
    )
    return list(session.exec(statement).all())


def get_prompt_log(session: Session, log_id: int) -> Optional[PromptLog]:
    return session.get(PromptLog, log_id)


def search_prompt_logs(
    session: Session, query: str, limit: int = 50
) -> list[PromptLog]:
    pattern = f"%{query}%"
    statement = (
        select(PromptLog)
        .where(
            col(PromptLog.prompt).ilike(pattern)
            | col(PromptLog.response).ilike(pattern)
            | col(PromptLog.model).ilike(pattern)
            | col(PromptLog.provider).ilike(pattern)
            | col(PromptLog.tags).ilike(pattern)
        )
        .order_by(col(PromptLog.created_at).desc())
        .limit(limit)
    )
    return list(session.exec(statement).all())
