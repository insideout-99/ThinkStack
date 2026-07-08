from app.db.repositories import FeedbackRepository
from app.db.session import SessionLocal


def _serialize_feedback(feedback) -> dict:
    return {
        "id": feedback.id,
        "query_log_id": feedback.query_log_id,
        "rating": feedback.rating,
        "comment": feedback.comment,
        "created_at": feedback.created_at.isoformat() if feedback.created_at else None,
    }


def create_feedback(payload: dict) -> dict | None:
    if SessionLocal is None:
        return None

    with SessionLocal() as db:
        feedback = FeedbackRepository(db).create_feedback(payload)
        return _serialize_feedback(feedback)


def list_feedback(limit: int = 100) -> list[dict]:
    if SessionLocal is None:
        return []

    with SessionLocal() as db:
        return [_serialize_feedback(feedback) for feedback in FeedbackRepository(db).list_feedback(limit=limit)]
