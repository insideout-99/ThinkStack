from app.db.repositories import FeedbackRepository
from sqlalchemy.exc import SQLAlchemyError

from app.db.session import SessionLocal, database_status


def _serialize_feedback(feedback) -> dict:
    return {
        "id": feedback.id,
        "query_log_id": feedback.query_log_id,
        "rating": feedback.rating,
        "comment": feedback.comment,
        "created_at": feedback.created_at.isoformat() if feedback.created_at else None,
    }


def create_feedback(payload: dict) -> dict | None:
    if SessionLocal is None or not database_status()["connected"]:
        return None

    try:
        with SessionLocal() as db:
            feedback = FeedbackRepository(db).create_feedback(payload)
            return _serialize_feedback(feedback)
    except SQLAlchemyError:
        return None


def list_feedback(limit: int = 100) -> list[dict]:
    if SessionLocal is None or not database_status()["connected"]:
        return []

    try:
        with SessionLocal() as db:
            return [_serialize_feedback(feedback) for feedback in FeedbackRepository(db).list_feedback(limit=limit)]
    except SQLAlchemyError:
        return []
