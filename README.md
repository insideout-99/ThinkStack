# ThinkStack

ThinkStack is an AI-powered enterprise knowledge management system. It lets users upload company documents or index webpages, then ask natural-language questions and receive answers grounded in the indexed knowledge base with citations.

## What It Does

- Uploads and indexes PDF, DOCX, TXT, and Markdown documents.
- Indexes webpage URLs by extracting clean page text.
- Stores uploaded files and webpage snapshots locally.
- Splits extracted content into searchable chunks.
- Generates vector embeddings with Gemini.
- Stores vectors in a local Qdrant database.
- Retrieves relevant chunks for user questions.
- Generates cited answers through a FastAPI RAG backend.
- Provides a React chat interface for document upload, webpage indexing, document listing, and Q&A.

## Current Phase

This repository currently implements Phase 2: production document processing.

Phase 2 expands the original PDF-only RAG MVP into a more complete ingestion pipeline with support for multiple document formats and webpages.

## Architecture Overview

```text
Documents / URLs
      |
      v
FastAPI Ingestion API
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
Retriever + Gemini Answer Generation
      |
      v
React Chat UI with Citations
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
      App.tsx
      index.css
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
- `POST /api/upload` - upload PDF, DOCX, TXT, or MD files
- `POST /api/url` - index a webpage URL
- `POST /api/query` - ask a question against the knowledge base
- `GET /api/documents` - list indexed documents

## Notes

Runtime folders such as uploads, Qdrant data, virtual environments, dependencies, build output, and local environment files are ignored by Git.
