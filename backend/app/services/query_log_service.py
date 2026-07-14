from app.db.repositories import QueryLogRepository
from sqlalchemy.exc import SQLAlchemyError

from app.db.session import SessionLocal, database_status


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
    if SessionLocal is None or not database_status()["connected"]:
        return None

    try:
        with SessionLocal() as db:
            log = QueryLogRepository(db).create_log(payload)
            return _serialize_query_log(log)
    except SQLAlchemyError:
        return None


def list_query_logs(limit: int = 100) -> list[dict]:
    if SessionLocal is None or not database_status()["connected"]:
        return []

    try:
        with SessionLocal() as db:
            return [_serialize_query_log(log) for log in QueryLogRepository(db).list_logs(limit=limit)]
    except SQLAlchemyError:
        return []
