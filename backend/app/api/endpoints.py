import os
import shutil
import tempfile
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from app.api.schemas import QueryRequest, URLRequest
from app.services.rag_service import RAGService
from app.services.metadata_service import parse_metadata_json

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

@router.get("/api/health")
def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "ThinkStack Backend v2"}

@router.post("/api/upload")
async def upload_document(file: UploadFile = File(...), metadata: str | None = Form(default=None)):
    """Uploads and indexes PDF, DOCX, TXT, or MD documents."""
    rag_service = get_rag_service()

    filename = os.path.basename(file.filename or "")
    if not filename:
        raise HTTPException(status_code=400, detail="Uploaded file must have a filename.")

    ext = os.path.splitext(filename.lower())[1]
    
    if ext not in [".pdf", ".docx", ".txt", ".md"]:
        raise HTTPException(
            status_code=400, 
            detail=f"Unsupported file format '{ext}'. Only PDF, DOCX, TXT, and MD are supported."
        )

    with tempfile.TemporaryDirectory(prefix="thinkstack_upload_") as temp_dir:
        temp_path = os.path.join(temp_dir, filename)

        try:
            with open(temp_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)

            # Process and ingest the document persistently
            document_metadata = parse_metadata_json(metadata)
            result = rag_service.ingest_file(temp_path, filename, metadata=document_metadata)
            return result
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Ingestion failed: {str(e)}")

@router.post("/api/url")
async def index_webpage(request: URLRequest):
    """Crawls a website URL, saves a local copy, and embeds its body text."""
    rag_service = get_rag_service()
        
    url_str = str(request.url).strip()
    if not url_str.startswith(("http://", "https://")):
        raise HTTPException(status_code=400, detail="Invalid URL protocol. Must start with http or https.")
        
    try:
        result = rag_service.ingest_url(url_str, metadata=request.metadata)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to index website URL: {str(e)}")

@router.post("/api/query")
async def query_knowledge_base(request: QueryRequest):
    """Queries the vector index and returns generative answers with cited metadata."""
    rag_service = get_rag_service()
        
    if not request.query.strip():
        raise HTTPException(status_code=400, detail="Query string cannot be empty.")

    try:
        result = rag_service.answer_query(request.query, filters=request.filters)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query resolution failed: {str(e)}")

@router.get("/api/documents")
async def get_documents():
    """Lists unique document inventory inside the vector database."""
    rag_service = get_rag_service()
        
    try:
        docs = rag_service.get_all_documents()
        return docs
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch documents: {str(e)}")
