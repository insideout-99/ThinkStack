import os
import shutil
import tempfile
import time
import uuid
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from app.api.schemas import FeedbackRequest, QueryRequest, URLRequest
from app.services.rag_service import RAGService
from app.services.metadata_service import parse_metadata_json
from app.config import MAX_UPLOAD_BYTES, UPLOADS_DIR
from app.services.database_document_service import (
    create_ingestion_event,
    list_documents as list_database_documents,
    list_ingestion_events,
    upsert_document_from_ingestion,
)
from app.services.feedback_service import create_feedback, list_feedback
from app.services.query_log_service import create_query_log, list_query_logs
from app.db.session import database_status

router = APIRouter()

# Centralized RAG service instance holder (initialized lazily)
_rag_service = None

def get_rag_service() -> RAGService:
    global _rag_service
    if _rag_service is None:
        try:
            _rag_service = RAGService()
        except Exception as e:
            raise HTTPException(
                status_code=500, 
                detail=f"Failed to initialize RAG Service database connection: {str(e)}"
            )
    return _rag_service


def _model_to_dict(model) -> dict | None:
    if model is None:
        return None

    if hasattr(model, "model_dump"):
        return model.model_dump(exclude_none=True)

    return model.dict(exclude_none=True)


def _persistence_details(document_id: str, result: dict, document_record: dict | None, event: dict | None) -> dict:
    """Expose enough state to diagnose a partial Qdrant/PostgreSQL write."""
    db_status = database_status()
    warnings = []
    if db_status["configured"] and not db_status["connected"]:
        warnings.append("Qdrant indexing completed, but PostgreSQL is unavailable. Re-index this source after PostgreSQL is restored.")
    elif db_status["connected"] and (document_record is None or event is None):
        warnings.append("Qdrant indexing completed, but one or more PostgreSQL records could not be saved. Check backend logs and re-index if needed.")

    return {
        "document_id": document_id,
        "qdrant_collection": result.get("qdrant_collection"),
        "document_record_id": document_record.get("id") if document_record else None,
        "ingestion_event_id": event.get("id") if event else None,
        "warnings": warnings,
    }

@router.get("/api/health")
def health_check():
    """Health check endpoint."""
    status = database_status()
    return {
        "status": "healthy",
        "service": "ThinkStack Backend v2",
        "database_configured": status["configured"],
        "database_connected": status["connected"],
    }

@router.post("/api/upload")
async def upload_document(file: UploadFile = File(...), metadata: str | None = Form(default=None)):
    """Uploads and indexes PDF, DOCX, TXT, or MD documents."""
    filename = os.path.basename(file.filename or "")
    if not filename:
        raise HTTPException(status_code=400, detail="Uploaded file must have a filename.")

    ext = os.path.splitext(filename.lower())[1]
    
    if ext not in [".pdf", ".docx", ".txt", ".md"]:
        raise HTTPException(
            status_code=400, 
            detail=f"Unsupported file format '{ext}'. Only PDF, DOCX, TXT, and MD are supported."
        )

    if file.size is not None and file.size > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail=f"Upload exceeds the {MAX_UPLOAD_BYTES // (1024 * 1024)} MiB size limit.")

    document_id = str(uuid.uuid4())
    source_info = os.path.join(UPLOADS_DIR, filename)
    document_metadata = None
    processing_record = None

    with tempfile.TemporaryDirectory(prefix="thinkstack_upload_") as temp_dir:
        temp_path = os.path.join(temp_dir, filename)

        try:
            document_metadata = parse_metadata_json(metadata)
            processing_record = upsert_document_from_ingestion({
                "source_name": filename,
                "source_type": ext.lstrip("."),
                "source_info": source_info,
                "metadata": _model_to_dict(document_metadata) or {},
                "chunks_count": 0,
                "qdrant_collection": "thinkstack_documents",
            }, document_id=document_id, status="processing")
            create_ingestion_event({
                "document_id": document_id if processing_record else None,
                "source_name": filename,
                "source_type": ext.lstrip("."),
                "source_info": source_info,
                "event_type": "file_upload",
                "status": "processing",
                "chunk_count": None,
                "metadata": _model_to_dict(document_metadata),
            })
            with open(temp_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)

            rag_service = get_rag_service()
            result = rag_service.ingest_file(
                temp_path,
                filename,
                metadata=document_metadata,
                document_id=document_id,
            )
            document_record = upsert_document_from_ingestion(result, document_id=document_id, status="indexed")
            indexed_event = create_ingestion_event({
                "document_id": document_id,
                "source_name": result.get("source_name", filename),
                "source_type": result.get("source_type", ext.lstrip(".")),
                "source_info": result.get("source_info"),
                "event_type": "file_upload",
                "status": "indexed",
                "chunk_count": result.get("chunks_count"),
                "metadata": result.get("metadata"),
            })
            if document_record:
                result["document_record"] = document_record
            result["status"] = "indexed"
            result["persistence"] = _persistence_details(document_id, result, document_record, indexed_event)
            return result
        except ValueError as e:
            upsert_document_from_ingestion({
                "source_name": filename, "source_type": ext.lstrip("."), "source_info": source_info,
                "metadata": _model_to_dict(document_metadata) or {}, "chunks_count": 0,
                "qdrant_collection": "thinkstack_documents",
            }, document_id=document_id, status="failed")
            create_ingestion_event({
                "document_id": document_id if processing_record else None,
                "source_name": filename,
                "source_type": ext.lstrip(".") or "unknown",
                "source_info": source_info,
                "event_type": "ingestion_failed",
                "status": "failed",
                "chunk_count": None,
                "error_message": str(e),
                "metadata": _model_to_dict(document_metadata),
            })
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            upsert_document_from_ingestion({
                "source_name": filename, "source_type": ext.lstrip("."), "source_info": source_info,
                "metadata": _model_to_dict(document_metadata) or {}, "chunks_count": 0,
                "qdrant_collection": "thinkstack_documents",
            }, document_id=document_id, status="failed")
            create_ingestion_event({
                "document_id": document_id if processing_record else None,
                "source_name": filename,
                "source_type": ext.lstrip(".") or "unknown",
                "source_info": source_info,
                "event_type": "ingestion_failed",
                "status": "failed",
                "chunk_count": None,
                "error_message": str(e),
                "metadata": _model_to_dict(document_metadata),
            })
            raise HTTPException(status_code=500, detail=f"Ingestion failed: {str(e)}")

@router.post("/api/url")
async def index_webpage(request: URLRequest):
    """Crawls a website URL, saves a local copy, and embeds its body text."""
    url_str = str(request.url).strip()
    if not url_str.startswith(("http://", "https://")):
        raise HTTPException(status_code=400, detail="Invalid URL protocol. Must start with http or https.")

    document_id = str(uuid.uuid4())
    metadata = _model_to_dict(request.metadata) or {}
    processing_record = None

    try:
        processing_record = upsert_document_from_ingestion({
            "source_name": url_str,
            "source_type": "url",
            "source_info": url_str,
            "metadata": metadata,
            "chunks_count": 0,
            "qdrant_collection": "thinkstack_documents",
        }, document_id=document_id, status="processing")
        create_ingestion_event({
            "document_id": document_id if processing_record else None,
            "source_name": url_str,
            "source_type": "url",
            "source_info": url_str,
            "event_type": "url_index",
            "status": "processing",
            "chunk_count": None,
            "metadata": metadata,
        })
        rag_service = get_rag_service()
        result = rag_service.ingest_url(url_str, metadata=request.metadata, document_id=document_id)
        document_record = upsert_document_from_ingestion(result, document_id=document_id, status="indexed")
        indexed_event = create_ingestion_event({
            "document_id": document_id,
            "source_name": result.get("source_name", url_str),
            "source_type": "url",
            "source_info": result.get("source_info", url_str),
            "event_type": "url_index",
            "status": "indexed",
            "chunk_count": result.get("chunks_count"),
            "metadata": result.get("metadata"),
        })
        if document_record:
            result["document_record"] = document_record
        result["status"] = "indexed"
        result["persistence"] = _persistence_details(document_id, result, document_record, indexed_event)
        return result
    except Exception as e:
        upsert_document_from_ingestion({
            "source_name": url_str, "source_type": "url", "source_info": url_str,
            "metadata": metadata, "chunks_count": 0, "qdrant_collection": "thinkstack_documents",
        }, document_id=document_id, status="failed")
        create_ingestion_event({
            "document_id": document_id if processing_record else None,
            "source_name": url_str,
            "source_type": "url",
            "source_info": url_str,
            "event_type": "ingestion_failed",
            "status": "failed",
            "chunk_count": None,
            "error_message": str(e),
            "metadata": metadata,
        })
        raise HTTPException(status_code=500, detail=f"Failed to index website URL: {str(e)}")

@router.post("/api/query")
async def query_knowledge_base(request: QueryRequest):
    """Queries the vector index and returns generative answers with cited metadata."""
    if not request.query.strip():
        raise HTTPException(status_code=400, detail="Query string cannot be empty.")

    rag_service = get_rag_service()

    started_at = time.perf_counter()

    try:
        result = rag_service.answer_query(request.query, filters=request.filters)
        latency_ms = int((time.perf_counter() - started_at) * 1000)
        query_log = create_query_log({
            "query": request.query,
            "filters": _model_to_dict(request.filters),
            "answer": result.get("answer"),
            "citations": result.get("citations", []),
            "latency_ms": latency_ms,
            "status": "success",
            "error_message": None,
        })
        if query_log:
            result["query_log_id"] = query_log["id"]
        return result
    except Exception as e:
        latency_ms = int((time.perf_counter() - started_at) * 1000)
        create_query_log({
            "query": request.query,
            "filters": _model_to_dict(request.filters),
            "answer": None,
            "citations": [],
            "latency_ms": latency_ms,
            "status": "failed",
            "error_message": str(e),
        })
        raise HTTPException(status_code=500, detail=f"Query resolution failed: {str(e)}")

@router.get("/api/documents")
async def get_documents():
    """Lists unique document inventory."""
    rag_service = get_rag_service()
        
    try:
        database_docs = list_database_documents()
        if database_docs is not None:
            return database_docs

        docs = rag_service.get_all_documents()
        return docs
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch documents: {str(e)}")


@router.get("/api/ingestion-events")
async def get_ingestion_events(limit: int = 100):
    """Development endpoint for recent ingestion history."""
    return list_ingestion_events(limit=limit)


@router.get("/api/query-logs")
async def get_query_logs(limit: int = 100):
    """Development endpoint for recent query logs."""
    return list_query_logs(limit=limit)


@router.post("/api/feedback")
async def submit_feedback(request: FeedbackRequest):
    """Stores user feedback for a generated answer."""
    if request.rating not in {"correct", "partially_correct", "incorrect", "wrong_source", "missing_citation", "hallucinated"}:
        raise HTTPException(status_code=400, detail="Invalid feedback rating.")

    feedback = create_feedback({
        "query_log_id": request.query_log_id,
        "rating": request.rating,
        "comment": request.comment,
    })
    if feedback is None:
        raise HTTPException(status_code=503, detail="DATABASE_URL is not configured; feedback storage is unavailable.")

    return {"status": "success", "feedback_id": feedback["id"], "feedback": feedback}


@router.get("/api/feedback")
async def get_feedback(limit: int = 100):
    """Development endpoint for recent feedback."""
    return list_feedback(limit=limit)
