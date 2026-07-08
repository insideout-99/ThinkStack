from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.db import models  # noqa: F401
from app.db.repositories import (
    DocumentRepository,
    FeedbackRepository,
    IngestionEventRepository,
    QueryLogRepository,
)


def create_test_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return Session()


def test_document_upsert_and_listing():
    db = create_test_session()
    repo = DocumentRepository(db)

    document = repo.upsert_document({
        "id": "doc-1",
        "source_name": "handbook.pdf",
        "source_type": "pdf",
        "source_info": "uploads/handbook.pdf",
        "department": "HR",
        "category": "Policy",
        "author": "People Ops",
        "tags": ["leave", "benefits"],
        "status": "indexed",
        "chunk_count": 4,
        "page_count": 2,
        "qdrant_collection": "thinkstack_documents",
    })

    assert document.id == "doc-1"
    assert document.chunk_count == 4

    updated = repo.upsert_document({
        "id": "doc-1",
        "source_name": "handbook.pdf",
        "source_type": "pdf",
        "source_info": "uploads/handbook.pdf",
        "department": "HR",
        "category": "Policy",
        "author": "People Ops",
        "tags": ["leave", "benefits", "pto"],
        "status": "indexed",
        "chunk_count": 6,
        "page_count": 3,
        "qdrant_collection": "thinkstack_documents",
    })

    assert updated.chunk_count == 6
    assert updated.tags == ["leave", "benefits", "pto"]

    repo.upsert_document({
        "id": "doc-2",
        "source_name": "old.md",
        "source_type": "md",
        "source_info": "uploads/old.md",
        "department": None,
        "category": None,
        "author": None,
        "tags": [],
        "status": "deleted",
        "chunk_count": 1,
        "page_count": 1,
        "qdrant_collection": "thinkstack_documents",
    })

    documents = repo.list_documents()
    assert [document.id for document in documents] == ["doc-1"]
    db.close()


def test_ingestion_event_insert():
    db = create_test_session()
    event = IngestionEventRepository(db).create_event({
        "document_id": None,
        "source_name": "https://example.com",
        "source_type": "url",
        "source_info": "https://example.com",
        "event_type": "url_index",
        "status": "success",
        "chunk_count": 1,
        "metadata": {"category": "Documentation"},
    })

    assert event.id
    assert event.metadata_payload == {"category": "Documentation"}
    assert event.status == "success"
    db.close()


def test_query_log_insert():
    db = create_test_session()
    log = QueryLogRepository(db).create_log({
        "query": "What is the leave policy?",
        "filters": {"department": "hr"},
        "answer": "Employees receive leave [1].",
        "citations": [{"document_name": "handbook.pdf"}],
        "latency_ms": 1200,
        "status": "success",
        "error_message": None,
    })

    assert log.id
    assert log.status == "success"
    assert log.citations == [{"document_name": "handbook.pdf"}]
    db.close()


def test_feedback_insert():
    db = create_test_session()
    feedback = FeedbackRepository(db).create_feedback({
        "query_log_id": None,
        "rating": "correct",
        "comment": "Citation is accurate.",
    })

    assert feedback.id
    assert feedback.rating == "correct"
    db.close()


if __name__ == "__main__":
    test_document_upsert_and_listing()
    test_ingestion_event_insert()
    test_query_log_insert()
    test_feedback_insert()
    print("Database repository tests passed.")
