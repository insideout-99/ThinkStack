from app.db.repositories import DocumentRepository, IngestionEventRepository
from app.db.session import SessionLocal


def _serialize_document(document) -> dict:
    return {
        "id": document.id,
        "name": document.source_name,
        "file_type": document.source_type,
        "source_info": document.source_info,
        "department": document.department,
        "category": document.category,
        "author": document.author,
        "tags": document.tags or [],
        "status": document.status,
        "chunk_count": document.chunk_count,
        "total_pages": document.page_count or 0,
        "qdrant_collection": document.qdrant_collection,
        "uploaded_at": document.created_at.isoformat() if document.created_at else None,
        "created_at": document.created_at.isoformat() if document.created_at else None,
        "updated_at": document.updated_at.isoformat() if document.updated_at else None,
    }


def _serialize_event(event) -> dict:
    return {
        "id": event.id,
        "document_id": event.document_id,
        "source_name": event.source_name,
        "source_type": event.source_type,
        "source_info": event.source_info,
        "event_type": event.event_type,
        "status": event.status,
        "chunk_count": event.chunk_count,
        "error_message": event.error_message,
        "metadata": event.metadata_payload,
        "created_at": event.created_at.isoformat() if event.created_at else None,
    }


def database_available() -> bool:
    return SessionLocal is not None


def upsert_document_from_ingestion(result: dict, document_id: str, status: str = "indexed") -> dict | None:
    if SessionLocal is None:
        return None

    metadata = result.get("metadata") or {}
    with SessionLocal() as db:
        document = DocumentRepository(db).upsert_document({
            "id": document_id,
            "source_name": result.get("source_name") or result.get("document_name") or "Unknown",
            "source_type": result.get("source_type") or result.get("file_type") or "unknown",
            "source_info": result.get("source_info"),
            "department": metadata.get("department"),
            "category": metadata.get("category"),
            "author": metadata.get("author"),
            "tags": metadata.get("tags") or [],
            "status": status,
            "chunk_count": result.get("chunks_count", 0),
            "page_count": result.get("page_count"),
            "qdrant_collection": result.get("qdrant_collection") or "thinkstack_documents",
        })
        return _serialize_document(document)


def create_ingestion_event(payload: dict) -> dict | None:
    if SessionLocal is None:
        return None

    with SessionLocal() as db:
        event = IngestionEventRepository(db).create_event(payload)
        return _serialize_event(event)


def list_documents() -> list[dict] | None:
    if SessionLocal is None:
        return None

    with SessionLocal() as db:
        return [_serialize_document(document) for document in DocumentRepository(db).list_documents()]


def list_ingestion_events(limit: int = 100) -> list[dict]:
    if SessionLocal is None:
        return []

    with SessionLocal() as db:
        return [_serialize_event(event) for event in IngestionEventRepository(db).list_events(limit=limit)]
