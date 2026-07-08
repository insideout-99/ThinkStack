from app.db.repositories import QueryLogRepository
from app.db.session import SessionLocal


def _serialize_query_log(log) -> dict:
    return {
        "id": log.id,
        "query": log.query,
        "filters": log.filters,
        "answer": log.answer,
        "citations": log.citations or [],
        "latency_ms": log.latency_ms,
        "status": log.status,
        "error_message": log.error_message,
        "created_at": log.created_at.isoformat() if log.created_at else None,
    }


def create_query_log(payload: dict) -> dict | None:
    if SessionLocal is None:
        return None

    with SessionLocal() as db:
        log = QueryLogRepository(db).create_log(payload)
        return _serialize_query_log(log)


def list_query_logs(limit: int = 100) -> list[dict]:
    if SessionLocal is None:
        return []

    with SessionLocal() as db:
        return [_serialize_query_log(log) for log in QueryLogRepository(db).list_logs(limit=limit)]
