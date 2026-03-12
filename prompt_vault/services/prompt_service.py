from typing import Optional, List

from sqlmodel import Session, select, col, func, text

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
    session: Session,
    skip: int = 0,
    limit: int = 50,
    provider: Optional[str] = None,
    model: Optional[str] = None,
    status: Optional[str] = None,
    tag: Optional[str] = None,
) -> List[PromptLog]:
    statement = select(PromptLog)
    if provider:
        statement = statement.where(PromptLog.provider == provider)
    if model:
        statement = statement.where(PromptLog.model == model)
    if status:
        statement = statement.where(PromptLog.status == status)
    if tag:
        statement = statement.where(col(PromptLog.tags).ilike(f"%{tag}%"))
    statement = (
        statement
        .order_by(col(PromptLog.created_at).desc())
        .offset(skip)
        .limit(limit)
    )
    return list(session.exec(statement).all())


def get_prompt_log(session: Session, log_id: int) -> Optional[PromptLog]:
    return session.get(PromptLog, log_id)


def search_prompt_logs(
    session: Session, query: str, limit: int = 50
) -> List[PromptLog]:
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


def update_tags(session: Session, log_id: int, tags: str) -> Optional[PromptLog]:
    entry = session.get(PromptLog, log_id)
    if not entry:
        return None
    entry.tags = tags
    session.add(entry)
    session.commit()
    session.refresh(entry)
    return entry


def get_total_count(session: Session) -> int:
    result = session.exec(select(func.count()).select_from(PromptLog))
    return result.one()


def get_provider_breakdown(session: Session) -> list:
    stmt = (
        select(PromptLog.provider, func.count().label("count"))
        .group_by(PromptLog.provider)
        .order_by(text("count DESC"))
    )
    return [{"provider": row[0], "count": row[1]} for row in session.exec(stmt).all()]


def get_model_breakdown(session: Session) -> list:
    stmt = (
        select(PromptLog.provider, PromptLog.model, func.count().label("count"))
        .group_by(PromptLog.provider, PromptLog.model)
        .order_by(text("count DESC"))
    )
    return [
        {"provider": row[0], "model": row[1], "count": row[2]}
        for row in session.exec(stmt).all()
    ]


def get_avg_latency_by_provider(session: Session) -> list:
    stmt = (
        select(PromptLog.provider, func.avg(PromptLog.latency_ms).label("avg_ms"))
        .group_by(PromptLog.provider)
    )
    return [
        {"provider": row[0], "avg_ms": round(row[1], 1)}
        for row in session.exec(stmt).all()
    ]


def get_avg_latency_by_model(session: Session) -> list:
    stmt = (
        select(
            PromptLog.provider,
            PromptLog.model,
            func.avg(PromptLog.latency_ms).label("avg_ms"),
            func.count().label("count"),
        )
        .group_by(PromptLog.provider, PromptLog.model)
        .order_by(text("avg_ms ASC"))
    )
    return [
        {"provider": row[0], "model": row[1], "avg_ms": round(row[2], 1), "count": row[3]}
        for row in session.exec(stmt).all()
    ]


def get_status_breakdown(session: Session) -> list:
    stmt = (
        select(PromptLog.status, func.count().label("count"))
        .group_by(PromptLog.status)
    )
    return [{"status": row[0], "count": row[1]} for row in session.exec(stmt).all()]


def get_daily_volume(session: Session, days: int = 30) -> list:
    stmt = text(
        "SELECT date(created_at) as day, count(*) as count "
        "FROM prompt_logs "
        "WHERE created_at >= date('now', :offset) "
        "GROUP BY day ORDER BY day"
    )
    result = session.exec(stmt, params={"offset": f"-{days} days"})
    return [{"day": row[0], "count": row[1]} for row in result.all()]


def get_token_totals(session: Session) -> dict:
    stmt = select(
        func.sum(PromptLog.prompt_tokens).label("prompt"),
        func.sum(PromptLog.completion_tokens).label("completion"),
        func.sum(PromptLog.total_tokens).label("total"),
    )
    row = session.exec(stmt).one()
    return {
        "prompt_tokens": row[0] or 0,
        "completion_tokens": row[1] or 0,
        "total_tokens": row[2] or 0,
    }


def get_today_count(session: Session) -> int:
    stmt = text(
        "SELECT count(*) FROM prompt_logs WHERE date(created_at) = date('now')"
    )
    return session.exec(stmt).one()[0]


def get_avg_latency(session: Session) -> float:
    stmt = select(func.avg(PromptLog.latency_ms))
    result = session.exec(stmt).one()
    return round(result or 0.0, 1)


def get_recent_grouped(session: Session, limit: int = 50) -> dict:
    """Return recent logs grouped into today / yesterday / older."""
    logs = get_prompt_logs(session, limit=limit)
    groups = {"today": [], "yesterday": [], "older": []}
    from datetime import date, timedelta
    today = date.today()
    yesterday = today - timedelta(days=1)
    for log in logs:
        log_date = log.created_at.date()
        if log_date == today:
            groups["today"].append(log)
        elif log_date == yesterday:
            groups["yesterday"].append(log)
        else:
            groups["older"].append(log)
    return groups


def get_distinct_providers(session: Session) -> List[str]:
    stmt = select(PromptLog.provider).distinct()
    return list(session.exec(stmt).all())


def get_distinct_models(session: Session) -> List[str]:
    stmt = select(PromptLog.model).distinct()
    return list(session.exec(stmt).all())
