# ThinkStack

ThinkStack is an AI-powered enterprise knowledge management system. It lets users upload company documents or index webpages, then ask natural-language questions and receive answers grounded in the indexed knowledge base with citations.

## What It Does

- Uploads and indexes PDF, DOCX, TXT, and Markdown documents.
- Indexes webpage URLs by extracting clean page text.
- Captures metadata for documents and webpages, including department, category, author, and tags.
- Stores uploaded files and webpage snapshots locally.
- Splits extracted content into searchable chunks.
- Generates vector embeddings with Gemini.
- Stores vectors in a local Qdrant database.
- Retrieves relevant chunks for user questions, with optional metadata filters.
- Generates cited answers through a FastAPI RAG backend.
- Provides a React chat interface for document upload, webpage indexing, metadata filtering, document listing, and Q&A.

## Current Phase

This repository currently implements Phase 3: metadata management.

Phase 3 expands the production document-processing RAG system with structured metadata capture, metadata-aware document inventory, and filtered retrieval. Users can organize indexed knowledge by department, category, author, tags, and source type, then constrain chat queries to matching documents.

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
```

## Tech Stack

- Frontend: React, TypeScript, Vite
- Backend: FastAPI, Python
- Vector Database: Qdrant local storage
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
        metadata_service.py
        rag_service.py
      config.py
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

Frontend checks:

```powershell
cd frontend
npm run lint
npm run build
```

## Notes

Runtime folders such as uploads, Qdrant data, virtual environments, dependencies, build output, and local environment files are ignored by Git.
