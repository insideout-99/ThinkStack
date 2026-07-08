# ThinkStack

ThinkStack is a local enterprise knowledge-base and RAG chat application. It indexes documents and webpages, stores their searchable chunks in Qdrant, and lets users ask natural-language questions with source-backed answers.

The current project is not just a basic upload demo. It now includes document ingestion, URL indexing, metadata management, filtered retrieval, citation display, PostgreSQL-backed operational history, query logging, and answer feedback.

## Current Status

ThinkStack currently works as a local full-stack RAG app:

- The frontend is a React/Vite chat workspace.
- The backend is a FastAPI API service.
- Gemini generates document embeddings and final answers.
- Qdrant stores the vector index locally.
- PostgreSQL stores structured records when `DATABASE_URL` is configured.
- The app can still run without PostgreSQL, but database-backed records, logs, and feedback are disabled in that mode.

Authentication, role-based access control, external connectors, analytics dashboards, and scheduled ingestion pipelines are not implemented yet.

## What It Can Do

### Ingest Knowledge

ThinkStack can index:

- PDF files
- DOCX files, including paragraph and table text
- TXT files
- Markdown files
- Webpage URLs

Uploaded files are copied into the backend uploads directory. Webpages are crawled, cleaned with BeautifulSoup, and saved as local text snapshots.

### Build A Searchable Vector Index

For every indexed source, the backend:

- extracts text
- groups text into page-like blocks
- splits content into overlapping chunks
- generates 768-dimensional Gemini embeddings
- stores chunks in the local Qdrant collection `thinkstack_documents`
- stores citation metadata with each chunk

If the same file or URL is indexed again, old Qdrant points for that source are removed before new chunks are inserted. That keeps repeated indexing from duplicating stale vector data.

### Manage Metadata

ThinkStack tracks metadata for every indexed source:

- department
- category
- author
- tags
- source type
- source name
- source path or URL
- upload timestamp

The backend can ask Gemini to infer department, category, author, and tags from document text. The frontend also provides optional override fields so the user can manually set metadata before indexing.

Metadata is normalized into filter-friendly keys and stored in Qdrant payloads. This allows filtered retrieval by department, category, author, tags, and source type.

### Ask Questions With Citations

When a user asks a question:

- the query is embedded with Gemini
- Qdrant retrieves the most similar chunks
- optional metadata filters are applied
- Gemini receives only the retrieved context
- the answer is generated with numbered inline citations
- the frontend renders citation markers and expandable source cards

Citation cards show the source document or URL, page/block number, metadata, score, and text snippet.

### Persist Records In PostgreSQL

When `DATABASE_URL` is set, PostgreSQL stores application records alongside Qdrant:

- `documents` stores indexed file and URL records
- `ingestion_events` stores upload, URL indexing, and failure history
- `query_logs` stores queries, filters, answers, citations, status, errors, and latency
- `feedback` stores user answer ratings
- `users` exists as a foundation for future authentication

The `/api/documents` endpoint uses PostgreSQL when available. If PostgreSQL is not configured, it falls back to listing documents from Qdrant.

### Collect Answer Feedback

Every assistant response can show feedback buttons if query logging is available. Supported ratings are:

- correct
- partially correct
- incorrect
- wrong source
- missing citation
- hallucinated

Feedback rows are only created after the user rates an answer. It is normal for `documents`, `ingestion_events`, and `query_logs` to contain data while `feedback` is empty.

## User Interface

The frontend has two main areas.

The sidebar contains:

- document upload
- webpage indexing
- AI metadata status
- optional metadata override fields
- indexed document list
- document type, chunk/page count, status, metadata, and tags

The main chat area contains:

- search filters for department, category, author, source type, and tags
- chat messages
- loading state while answers are generated
- inline citation references
- expandable source cards
- feedback controls below assistant answers
- toast notifications for upload, indexing, and query errors

## Architecture

```text
Document file or webpage URL
        |
        v
FastAPI ingestion endpoint
        |
        v
Document loader
PDF / DOCX / TXT / Markdown / URL
        |
        v
Text extraction and chunking
        |
        v
Gemini metadata suggestion
        |
        v
Gemini embedding generation
        |
        +--------------------------+
        |                          |
        v                          v
Qdrant local vector DB        PostgreSQL
Chunk vectors                 Document records
Chunk text                    Ingestion events
Citation metadata             Query logs
Filter metadata               Feedback
        |
        v
Filtered similarity search
        |
        v
Gemini answer generation
        |
        v
React chat UI
```

Qdrant is responsible for semantic retrieval. PostgreSQL is responsible for structured application history and records.

## Tech Stack

- Frontend: React 19, TypeScript, Vite
- Backend: FastAPI, Uvicorn, Python
- AI: Gemini embeddings and Gemini 2.5 Flash answer generation
- Vector database: Qdrant local mode
- Relational database: PostgreSQL
- ORM and migrations: SQLAlchemy, Alembic, psycopg
- File parsing: pypdf, python-docx
- Web parsing: requests, BeautifulSoup

## Repository Structure

```text
ThinkStack/
  backend/
    main.py
    requirements.txt
    test_api.py
    test_rag.py
    alembic.ini
    alembic/
      env.py
      versions/
        20260708_0001_create_phase4_tables.py
    app/
      api/
        endpoints.py
        schemas.py
      db/
        base.py
        models.py
        repositories.py
        session.py
      services/
        database_document_service.py
        document_loaders.py
        feedback_service.py
        metadata_service.py
        query_log_service.py
        rag_service.py
      config.py
  frontend/
    package.json
    vite.config.ts
    src/
      App.tsx
      main.tsx
      metadata.ts
      index.css
      components/
        ChatInterface.tsx
        DocumentList.tsx
        DocumentUpload.tsx
        FeedbackControls.tsx
        MetadataFilters.tsx
```

## Backend Setup

```powershell
cd backend
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
```

Create `backend/.env`:

```env
GEMINI_API_KEY=your_gemini_api_key
DATABASE_URL=postgresql+psycopg://postgres:your_postgres_password@localhost:5432/thinkstack
QDRANT_PATH=data/qdrant
```

`GEMINI_API_KEY` is required for embeddings, metadata suggestion, and answer generation.

`DATABASE_URL` is optional for vector-only local usage, but required for PostgreSQL document records, ingestion history, query logs, and feedback.

Use `backend/.env.example` as the safe template. Keep real keys and passwords only in `backend/.env`.

## PostgreSQL Setup

Create the database:

```powershell
& "C:\Program Files\PostgreSQL\18\bin\createdb.exe" -U postgres thinkstack
```

If your installed PostgreSQL version is different, replace `18` with your version.

Run migrations:

```powershell
cd C:\Users\hp\Desktop\ThinkStack\backend
.\venv\Scripts\alembic.exe upgrade head
```

Verify the tables:

```powershell
& "C:\Program Files\PostgreSQL\18\bin\psql.exe" -U postgres -d thinkstack -c "\dt"
```

Expected tables:

```text
alembic_version
documents
feedback
ingestion_events
query_logs
users
```

## Run The App

Start the backend:

```powershell
cd backend
.\venv\Scripts\python.exe main.py
```

Backend URL:

```text
http://localhost:8000
```

Start the frontend in a second terminal:

```powershell
cd frontend
npm install
npm run dev
```

If PowerShell blocks `npm.ps1`, run:

```powershell
npm.cmd run dev
```

Frontend URL:

```text
http://localhost:5173
```

## API Endpoints

- `GET /api/health` returns service health and whether the database is configured.
- `POST /api/upload` uploads and indexes a PDF, DOCX, TXT, or Markdown file.
- `POST /api/url` indexes a webpage URL.
- `POST /api/query` answers a question using indexed content and optional filters.
- `GET /api/documents` lists indexed documents.
- `GET /api/ingestion-events` lists recent ingestion events.
- `GET /api/query-logs` lists recent query logs.
- `POST /api/feedback` saves feedback for a logged answer.
- `GET /api/feedback` lists recent feedback.

## Query Filters

The query endpoint accepts optional filters:

```json
{
  "query": "What is the leave policy?",
  "filters": {
    "department": "HR",
    "category": "Policy",
    "author": "People Ops",
    "tags": ["leave", "benefits"],
    "source_type": "pdf"
  }
}
```

`source_type` can be:

```text
pdf
docx
txt
md
url
```

If no filters are provided, ThinkStack searches the full Qdrant collection.

## Verification

Backend syntax check:

```powershell
cd backend
.\venv\Scripts\python.exe -m compileall app main.py test_api.py test_rag.py test_database.py
.\venv\Scripts\python.exe test_database.py
```

Database migration check:

```powershell
cd backend
.\venv\Scripts\alembic.exe upgrade head
```

Frontend build:

```powershell
cd frontend
npm.cmd run build
```

## Local Runtime Data

The following files and folders are local runtime data and should not be committed:

- `backend/.env`
- backend upload files
- backend URL snapshots
- local Qdrant data
- Python virtual environments
- `frontend/node_modules`
- frontend build output
