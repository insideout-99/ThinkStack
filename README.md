# ThinkStack

ThinkStack is an AI-powered enterprise knowledge management system. It lets users upload company documents or index webpages, then ask natural-language questions and receive answers grounded in the indexed knowledge base with citations.

## What It Does

- Uploads and indexes PDF, DOCX, TXT, and Markdown documents.
- Indexes webpage URLs by extracting clean page text.
- Captures metadata for documents and webpages, including department, category, author, and tags.
- Stores uploaded files and webpage snapshots locally.
- Optionally persists document inventory, ingestion history, query logs, and answer feedback in PostgreSQL.
- Splits extracted content into searchable chunks.
- Generates vector embeddings with Gemini.
- Stores vectors in a local Qdrant database.
- Retrieves relevant chunks for user questions, with optional metadata filters.
- Generates cited answers through a FastAPI RAG backend.
- Provides a React chat interface for document upload, webpage indexing, metadata filtering, document listing, and Q&A.

## Current Phase

This repository currently implements Phase 4: persistent PostgreSQL history and feedback.

Phase 4 keeps Qdrant as the vector database and adds a relational persistence layer for operational data. When `DATABASE_URL` is configured, ThinkStack stores indexed document records, ingestion events, query logs with citations and latency, and answer feedback. If `DATABASE_URL` is omitted, the app still runs with the Phase 3 local Qdrant behavior and skips PostgreSQL-only storage.

## Architecture Overview

```text
Documents / URLs
      |
      v
FastAPI Ingestion API + Metadata Capture
      |
      v
Document Loaders and Text Extraction
      |
      v
Chunking and Metadata Enrichment
      |
      v
Gemini Embeddings
      |
      v
Qdrant Vector Database
      |
      v
Filtered Retriever + Gemini Answer Generation
      |
      v
React Chat UI with Metadata Filters and Citations

PostgreSQL, when configured, stores document inventory, ingestion events, query logs, and feedback alongside the vector workflow.
```

## Tech Stack

- Frontend: React, TypeScript, Vite
- Backend: FastAPI, Python
- Vector Database: Qdrant local storage
- Relational Database: PostgreSQL with SQLAlchemy and Alembic
- AI: Gemini embeddings and Gemini answer generation
- Document Processing: pypdf, python-docx, BeautifulSoup

## Project Structure

```text
ThinkStack/
  backend/
    app/
      api/
        endpoints.py
        schemas.py
      services/
        document_loaders.py
        database_document_service.py
        feedback_service.py
        metadata_service.py
        query_log_service.py
        rag_service.py
      db/
        base.py
        models.py
        repositories.py
        session.py
      config.py
    alembic/
    main.py
    requirements.txt
    test_api.py
    test_rag.py
  frontend/
    src/
      components/
        ChatInterface.tsx
        DocumentList.tsx
        DocumentUpload.tsx
        FeedbackControls.tsx
        MetadataFilters.tsx
      App.tsx
      index.css
      metadata.ts
    package.json
    vite.config.ts
```

## Local Setup

### Backend

```powershell
cd backend
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
```

Create `backend/.env`:

```env
GEMINI_API_KEY=your_api_key_here
DATABASE_URL=postgresql+psycopg://postgres:your_postgres_password@localhost:5432/thinkstack
```

`DATABASE_URL` is optional. Leave it unset to use local Qdrant-only persistence.

Create the local PostgreSQL database before running migrations:

```powershell
& "C:\Program Files\PostgreSQL\18\bin\createdb.exe" -U postgres thinkstack
```

Run database migrations when using PostgreSQL:

```powershell
cd backend
.\venv\Scripts\alembic.exe upgrade head
```

Verify the Phase 4 tables:

```powershell
& "C:\Program Files\PostgreSQL\18\bin\psql.exe" -U postgres -d thinkstack -c "\dt"
```

Run the backend:

```powershell
python main.py
```

Backend URL:

```text
http://localhost:8000
```

### Frontend

```powershell
cd frontend
npm install
npm run dev
```

Frontend URL:

```text
http://localhost:5173
```

## API Endpoints

- `GET /api/health` - health check
- `POST /api/upload` - upload PDF, DOCX, TXT, or MD files with optional metadata
- `POST /api/url` - index a webpage URL with optional metadata
- `POST /api/query` - ask a question against the knowledge base with optional metadata filters
- `GET /api/documents` - list indexed documents with metadata
- `GET /api/ingestion-events` - list recent ingestion events when PostgreSQL is configured
- `GET /api/query-logs` - list recent query logs when PostgreSQL is configured
- `POST /api/feedback` - store answer feedback for a logged query
- `GET /api/feedback` - list recent answer feedback when PostgreSQL is configured

## Metadata

ThinkStack supports document-level metadata during file upload and URL indexing:

```json
{
  "department": "HR",
  "category": "Policy",
  "author": "People Ops",
  "tags": ["leave", "benefits", "handbook"]
}
```

Metadata is stored on each indexed chunk in Qdrant and returned with document listings and citations.

Supported query filters:

```json
{
  "department": "Engineering",
  "category": "Standards",
  "author": "Platform Team",
  "tags": ["python", "backend"],
  "source_type": "docx"
}
```

Filters are optional. If no filters are supplied, ThinkStack searches the full knowledge base.

## Feedback

Query responses include `query_log_id` when PostgreSQL logging is enabled:

```json
{
  "answer": "Employees receive 25 days of paid time off [1].",
  "citations": [],
  "query_log_id": "0bd7d3f6-0d2f-4dd8-b517-2cfa87a3dfc5"
}
```

The frontend uses that ID to submit feedback:

```json
{
  "query_log_id": "0bd7d3f6-0d2f-4dd8-b517-2cfa87a3dfc5",
  "rating": "correct",
  "comment": null
}
```

Supported ratings are `correct`, `partially_correct`, `incorrect`, `wrong_source`, `missing_citation`, and `hallucinated`.

Feedback rows are created only after a user rates an answer. It is normal for the feedback endpoint or `answer_feedback` table to be empty when documents, ingestion events, and query logs already contain data.

### Upload With Metadata

File uploads send metadata as a JSON string in multipart form data:

```powershell
$metadata = '{"department":"HR","category":"Policy","author":"People Ops","tags":["leave","benefits"]}'

Invoke-RestMethod `
  -Uri "http://localhost:8000/api/upload" `
  -Method Post `
  -Form @{
    file = Get-Item ".\handbook.pdf"
    metadata = $metadata
  }
```

### Query With Filters

```powershell
$body = @{
  query = "What is the leave policy?"
  filters = @{
    department = "HR"
    tags = @("leave")
  }
} | ConvertTo-Json -Depth 5

Invoke-RestMethod `
  -Uri "http://localhost:8000/api/query" `
  -Method Post `
  -ContentType "application/json" `
  -Body $body
```

## Verification

Backend checks:

```powershell
cd backend
.\venv\Scripts\python.exe -m compileall app main.py test_api.py test_rag.py
```

Phase 4 PostgreSQL check:

```powershell
cd backend
.\venv\Scripts\alembic.exe upgrade head
& "C:\Program Files\PostgreSQL\18\bin\psql.exe" -U postgres -d thinkstack -c "\dt"
```

Frontend checks:

```powershell
cd frontend
npm run lint
npm run build
```

## Notes

Runtime folders such as uploads, Qdrant data, virtual environments, dependencies, build output, and local environment files are ignored by Git.
