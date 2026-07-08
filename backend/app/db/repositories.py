from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.db.models import Document, Feedback, IngestionEvent, QueryLog


class DocumentRepository:
    def __init__(self, db: Session):
        self.db = db

    def upsert_document(self, payload: dict) -> Document:
        document = self.db.get(Document, payload["id"])
        if document is None:
            document = Document(id=payload["id"], qdrant_collection=payload["qdrant_collection"], source_name=payload["source_name"], source_type=payload["source_type"])
            self.db.add(document)

        for key, value in payload.items():
            setattr(document, key, value)

        self.db.commit()
        self.db.refresh(document)
        return document

    def list_documents(self, limit: int = 500) -> list[Document]:
        stmt = select(Document).where(Document.status != "deleted").order_by(desc(Document.updated_at)).limit(limit)
        return list(self.db.scalars(stmt))


class IngestionEventRepository:
    def __init__(self, db: Session):
        self.db = db

    def create_event(self, payload: dict) -> IngestionEvent:
        if "metadata" in payload:
            payload = {**payload, "metadata_payload": payload.pop("metadata")}
        event = IngestionEvent(**payload)
        self.db.add(event)
        self.db.commit()
        self.db.refresh(event)
        return event

    def list_events(self, limit: int = 100) -> list[IngestionEvent]:
        stmt = select(IngestionEvent).order_by(desc(IngestionEvent.created_at)).limit(limit)
        return list(self.db.scalars(stmt))


class QueryLogRepository:
    def __init__(self, db: Session):
        self.db = db

    def create_log(self, payload: dict) -> QueryLog:
        log = QueryLog(**payload)
        self.db.add(log)
        self.db.commit()
        self.db.refresh(log)
        return log

    def list_logs(self, limit: int = 100) -> list[QueryLog]:
        stmt = select(QueryLog).order_by(desc(QueryLog.created_at)).limit(limit)
        return list(self.db.scalars(stmt))


class FeedbackRepository:
    def __init__(self, db: Session):
        self.db = db

    def create_feedback(self, payload: dict) -> Feedback:
        feedback = Feedback(**payload)
        self.db.add(feedback)
        self.db.commit()
        self.db.refresh(feedback)
        return feedback

    def list_feedback(self, limit: int = 100) -> list[Feedback]:
        stmt = select(Feedback).order_by(desc(Feedback.created_at)).limit(limit)
        return list(self.db.scalars(stmt))
