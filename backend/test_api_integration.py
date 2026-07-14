from unittest.mock import patch

from fastapi.testclient import TestClient

from main import app


client = TestClient(app)


class FakeRAGService:
    def ingest_file(self, source_path, original_filename, metadata=None, document_id=None):
        return {
            "status": "success",
            "message": f"Successfully indexed {original_filename}",
            "chunks_count": 2,
            "page_count": 1,
            "document_id": document_id,
            "source_name": original_filename,
            "source_type": "pdf",
            "source_info": source_path,
            "qdrant_collection": "thinkstack_documents",
            "metadata": {
                "department": "HR",
                "category": "Policy",
                "author": "People Ops",
                "tags": ["leave", "benefits"],
            },
        }

    def ingest_url(self, url, metadata=None, document_id=None):
        return {
            "status": "success",
            "message": f"Successfully indexed {url}",
            "chunks_count": 1,
            "page_count": 1,
            "document_id": document_id,
            "source_name": "Example Domain",
            "source_type": "url",
            "source_info": url,
            "qdrant_collection": "thinkstack_documents",
            "metadata": {
                "department": "General",
                "category": "Documentation",
                "author": None,
                "tags": ["example"],
            },
        }

    def answer_query(self, query, filters=None):
        return {
            "answer": "Employees receive 25 days of paid time off [1].",
            "citations": [
                {
                    "score": 0.98,
                    "text": "Employees receive 25 days of paid time off.",
                    "page_number": 2,
                    "document_name": "handbook.pdf",
                    "file_type": "pdf",
                    "source_info": "uploads/handbook.pdf",
                    "document_id": "doc-1",
                    "department": "HR",
                    "category": "Policy",
                    "author": "People Ops",
                    "tags": ["leave", "benefits"],
                    "uploaded_at": "2026-07-08T00:00:00Z",
                }
            ],
        }


def test_health_endpoint():
    response = client.get("/api/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "database_configured" in data


def test_empty_query_rejected():
    response = client.post("/api/query", json={"query": "   "})

    assert response.status_code == 400
    assert response.json()["detail"] == "Query string cannot be empty."


def test_invalid_feedback_rating_rejected():
    response = client.post(
        "/api/feedback",
        json={
            "query_log_id": None,
            "rating": "bad_rating",
            "comment": None,
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid feedback rating."


def test_unsupported_upload_file_type_rejected():
    response = client.post(
        "/api/upload",
        files={
            "file": ("malware.exe", b"fake content", "application/octet-stream"),
        },
    )

    assert response.status_code == 400
    assert "Unsupported file format" in response.json()["detail"]


def test_oversized_upload_is_rejected():
    with patch("app.api.endpoints.MAX_UPLOAD_BYTES", 4):
        response = client.post(
            "/api/upload",
            files={"file": ("large.txt", b"more than four bytes", "text/plain")},
        )

    assert response.status_code == 413
    assert "size limit" in response.json()["detail"]


def test_upload_success_uses_rag_and_persistence_hooks():
    with patch("app.api.endpoints.get_rag_service", return_value=FakeRAGService()), patch(
        "app.api.endpoints.upsert_document_from_ingestion",
        return_value={
            "id": "doc-1",
            "name": "handbook.pdf",
            "file_type": "pdf",
            "status": "indexed",
        },
    ), patch("app.api.endpoints.create_ingestion_event", return_value={"id": "evt-1"}) as create_event:
        response = client.post(
            "/api/upload",
            files={
                "file": ("handbook.pdf", b"fake pdf bytes", "application/pdf"),
            },
            data={
                "metadata": '{"department":"HR","category":"Policy","author":"People Ops","tags":["leave","benefits"]}',
            },
        )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "indexed"
    assert data["document_record"]["id"] == "doc-1"
    assert data["chunks_count"] == 2
    assert data["persistence"]["qdrant_collection"] == "thinkstack_documents"
    assert create_event.called


def test_url_index_success_uses_rag_and_persistence_hooks():
    with patch("app.api.endpoints.get_rag_service", return_value=FakeRAGService()), patch(
        "app.api.endpoints.upsert_document_from_ingestion",
        return_value={
            "id": "doc-2",
            "name": "Example Domain",
            "file_type": "url",
            "status": "indexed",
        },
    ), patch("app.api.endpoints.create_ingestion_event", return_value={"id": "evt-2"}) as create_event:
        response = client.post(
            "/api/url",
            json={
                "url": "https://example.com",
                "metadata": {
                    "department": "General",
                    "category": "Documentation",
                    "author": None,
                    "tags": ["example"],
                },
            },
        )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "indexed"
    assert data["document_record"]["id"] == "doc-2"
    assert data["source_type"] == "url"
    assert create_event.called


def test_failed_upload_records_failed_event():
    failing_rag = FakeRAGService()
    failing_rag.ingest_file = lambda *args, **kwargs: (_ for _ in ()).throw(ValueError("Unreadable document"))

    with patch("app.api.endpoints.get_rag_service", return_value=failing_rag), patch(
        "app.api.endpoints.upsert_document_from_ingestion", return_value={"id": "doc-3"}
    ), patch("app.api.endpoints.create_ingestion_event", return_value={"id": "evt-3"}) as create_event:
        response = client.post(
            "/api/upload",
            files={"file": ("bad.pdf", b"fake pdf bytes", "application/pdf")},
        )

    assert response.status_code == 400
    assert any(call.args[0]["status"] == "failed" for call in create_event.call_args_list)


def test_query_success_returns_log_id():
    with patch("app.api.endpoints.get_rag_service", return_value=FakeRAGService()), patch(
        "app.api.endpoints.create_query_log",
        return_value={
            "id": "log-1",
            "query": "What is the leave policy?",
            "filters": None,
            "answer": "Employees receive 25 days of paid time off [1].",
            "citations": [],
            "latency_ms": 11,
            "status": "success",
            "error_message": None,
        },
    ):
        response = client.post("/api/query", json={"query": "What is the leave policy?"})

    assert response.status_code == 200
    data = response.json()
    assert data["answer"].startswith("Employees receive 25 days")
    assert data["query_log_id"] == "log-1"
    assert data["citations"]


def test_feedback_success_returns_saved_record():
    with patch(
        "app.api.endpoints.create_feedback",
        return_value={
            "id": "feedback-1",
            "query_log_id": "log-1",
            "rating": "correct",
            "comment": None,
            "created_at": "2026-07-08T00:00:00Z",
        },
    ):
        response = client.post(
            "/api/feedback",
            json={
                "query_log_id": "log-1",
                "rating": "correct",
                "comment": None,
            },
        )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["feedback_id"] == "feedback-1"


def test_documents_endpoint_uses_database_records_when_available():
    with patch(
        "app.api.endpoints.list_database_documents",
        return_value=[
            {
                "id": "doc-1",
                "name": "handbook.pdf",
                "file_type": "pdf",
                "source_info": "uploads/handbook.pdf",
                "department": "HR",
                "category": "Policy",
                "author": "People Ops",
                "tags": ["leave", "benefits"],
                "status": "indexed",
                "chunk_count": 2,
                "total_pages": 1,
                "qdrant_collection": "thinkstack_documents",
                "uploaded_at": "2026-07-08T00:00:00Z",
                "created_at": "2026-07-08T00:00:00Z",
                "updated_at": "2026-07-08T00:00:00Z",
            }
        ],
    ), patch("app.api.endpoints.get_rag_service", return_value=FakeRAGService()):
        response = client.get("/api/documents")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["name"] == "handbook.pdf"


if __name__ == "__main__":
    test_health_endpoint()
    test_empty_query_rejected()
    test_invalid_feedback_rating_rejected()
    test_unsupported_upload_file_type_rejected()
    test_oversized_upload_is_rejected()
    test_upload_success_uses_rag_and_persistence_hooks()
    test_url_index_success_uses_rag_and_persistence_hooks()
    test_failed_upload_records_failed_event()
    test_query_success_returns_log_id()
    test_feedback_success_returns_saved_record()
    test_documents_endpoint_uses_database_records_when_available()
    print("API integration tests passed.")
