import os
import uuid
import shutil
import re
import time
import google.generativeai as genai
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, FieldCondition, Filter, MatchAny, MatchValue, PointStruct, VectorParams

# Import configurations
from app.config import GEMINI_API_KEY, QDRANT_PATH, UPLOADS_DIR, URL_SNAPSHOTS_DIR
# Import loaders
from app.services.document_loaders import load_pdf, load_docx, load_text_or_md, load_url
from app.api.schemas import DocumentMetadata, QueryFilters
from app.services.metadata_service import (
    merge_document_metadata,
    normalize_document_metadata,
    normalize_query_filters,
)

COLLECTION_NAME = "thinkstack_documents"
GEMINI_REQUEST_TIMEOUT_SECONDS = 45

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

class RAGService:
    def __init__(self):
        # Initialize Qdrant Client in local persistence mode
        self.qdrant_client = QdrantClient(path=QDRANT_PATH)
        self._ensure_collection()

    def _ensure_collection(self):
        """Creates the collection in Qdrant if it doesn't already exist."""
        try:
            if not self.qdrant_client.collection_exists(COLLECTION_NAME):
                self.qdrant_client.create_collection(
                    collection_name=COLLECTION_NAME,
                    vectors_config=VectorParams(
                        size=768,  # gemini-embedding-001 dimension size
                        distance=Distance.COSINE
                    )
                )
        except Exception as e:
            print(f"Error ensuring Qdrant collection: {e}")

    def split_text_into_chunks(self, pages: list[dict], chunk_size: int = 800, chunk_overlap: int = 150) -> list[dict]:
        """Split text into manageable overlapping chunks while preserving page number metadata."""
        if chunk_overlap >= chunk_size:
            raise ValueError("chunk_overlap must be smaller than chunk_size")

        chunks = []
        for page in pages:
            text = page["text"]
            page_num = page["page_number"]
            
            # Remove redundant whitespaces
            text = " ".join(text.split())
            if not text:
                continue

            # Sliding window text splitting
            start = 0
            while start < len(text):
                end = start + chunk_size
                chunk_str = text[start:end]
                
                # Prevent cutting words by back-tracking to nearest space
                if end < len(text):
                    last_space = chunk_str.rfind(" ")
                    if last_space != -1 and last_space > (chunk_size // 2):
                        end = start + last_space
                        chunk_str = text[start:end]

                chunks.append({
                    "text": chunk_str.strip(),
                    "page_number": page_num
                })

                if end >= len(text):
                    break

                step = max(1, (end - start) - chunk_overlap)
                start += step
        return chunks

    def get_embeddings(self, texts: list[str]) -> list[list[float]]:
        """Generates embeddings for a batch of texts using gemini-embedding-001."""
        if not GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY environment variable is not set in backend/.env")

        return self._embed_with_retry(
            content=texts,
            task_type="retrieval_document",
            error_label="embeddings",
        )

    def get_query_embedding(self, query: str) -> list[float]:
        """Generates embedding for a search query."""
        if not GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY environment variable is not set in backend/.env")

        return self._embed_with_retry(
            content=query,
            task_type="retrieval_query",
            error_label="query embedding",
        )

    def _embed_with_retry(self, content, task_type: str, error_label: str):
        """Call Gemini embeddings and wait through short per-minute quota windows."""
        max_attempts = 4

        for attempt in range(1, max_attempts + 1):
            try:
                result = genai.embed_content(
                    model="models/gemini-embedding-001",
                    content=content,
                    task_type=task_type,
                    output_dimensionality=768,
                    request_options={"timeout": GEMINI_REQUEST_TIMEOUT_SECONDS},
                )
                return result["embedding"]
            except Exception as e:
                error_text = str(e)
                is_rate_limited = "429" in error_text or "quota" in error_text.lower()
                if not is_rate_limited or attempt == max_attempts:
                    raise RuntimeError(f"Error generating {error_label} via Gemini API: {error_text}")

                retry_seconds = self._extract_retry_delay(error_text) or min(60, 10 * attempt)
                print(f"Gemini rate limit hit while generating {error_label}. Retrying in {retry_seconds} seconds...")
                time.sleep(retry_seconds)

        raise RuntimeError(f"Error generating {error_label} via Gemini API after retries")

    def _extract_retry_delay(self, error_text: str) -> int | None:
        match = re.search(r"retry_delay\s*\{\s*seconds:\s*(\d+)", error_text)
        if not match:
            return None

        return int(match.group(1)) + 2

    def _suggest_metadata(self, pages: list[dict], source_name: str, file_type: str) -> DocumentMetadata:
        """Use Gemini to infer metadata for enterprise document search."""
        if not GEMINI_API_KEY:
            return DocumentMetadata()

        sample_text = " ".join(page.get("text", "") for page in pages)
        sample_text = " ".join(sample_text.split())[:5000]
        if not sample_text:
            return DocumentMetadata()

        prompt = f"""
Analyze this document and infer concise metadata for enterprise knowledge search.

Source name: {source_name}
Source type: {file_type}

Return ONLY valid JSON with this exact shape:
{{
  "department": string or null,
  "category": string or null,
  "author": string or null,
  "tags": string[]
}}

Rules:
- department should be a broad business area if obvious, such as HR, Engineering, Finance, Legal, Sales, Marketing, Operations, Product, Research, or General.
- category should describe the document type or topic, such as Policy, Handbook, Report, Standards, Documentation, Research, Finance, or Guide.
- author should be null unless clearly stated.
- tags should contain 3 to 8 short lowercase topic tags.
- Do not invent a specific person or company as author.

Document text:
{sample_text}
"""
        try:
            model = genai.GenerativeModel("gemini-2.5-flash")
            response = model.generate_content(
                prompt,
                request_options={"timeout": GEMINI_REQUEST_TIMEOUT_SECONDS},
            )
            raw_text = response.text.strip()
            json_match = re.search(r"\{.*\}", raw_text, re.DOTALL)
            if not json_match:
                return DocumentMetadata()

            import json
            payload = json.loads(json_match.group(0))
            return DocumentMetadata(**payload)
        except Exception as e:
            print(f"Metadata suggestion failed for {source_name}: {e}")
            return DocumentMetadata()

    def _resolve_metadata(
        self,
        user_metadata: DocumentMetadata | None,
        pages: list[dict],
        source_name: str,
        file_type: str,
    ) -> DocumentMetadata:
        suggested_metadata = self._suggest_metadata(pages, source_name, file_type)
        return merge_document_metadata(user_metadata, suggested_metadata)

    def ingest_file(self, source_path: str, original_filename: str, metadata: DocumentMetadata | None = None) -> dict:
        """Parses a file (PDF, DOCX, TXT, MD), saves it in uploads, and indexes it."""
        ext = os.path.splitext(original_filename.lower())[1]
        
        # Save file persistently in the uploads folder
        dest_path = os.path.join(UPLOADS_DIR, original_filename)
        # Avoid file locking issues when copying the same file
        if os.path.abspath(source_path) != os.path.abspath(dest_path):
            shutil.copy2(source_path, dest_path)

        # Select parser
        if ext == ".pdf":
            pages = load_pdf(dest_path)
            file_type = "pdf"
        elif ext == ".docx":
            pages = load_docx(dest_path)
            file_type = "docx"
        elif ext in [".txt", ".md"]:
            pages = load_text_or_md(dest_path)
            file_type = "txt" if ext == ".txt" else "md"
        else:
            raise ValueError(f"Unsupported file format: {ext}")

        chunks = self.split_text_into_chunks(pages)
        if not chunks:
            return {"status": "success", "message": f"Document {original_filename} had no text.", "chunks_count": 0}

        metadata = self._resolve_metadata(metadata, pages, original_filename, file_type)

        # Index chunks in Qdrant. Existing points for the same file are removed first
        # so re-uploading a file replaces stale content instead of duplicating it.
        normalized_metadata = normalize_document_metadata(
            metadata=metadata,
            source_type=file_type,
            source_name=original_filename,
            source_info=dest_path,
        )
        return self._index_chunks_in_qdrant(
            chunks,
            original_filename,
            file_type,
            source_info=dest_path,
            metadata=normalized_metadata,
        )

    def ingest_url(self, url: str, metadata: DocumentMetadata | None = None) -> dict:
        """Crawls a URL, stores a text snapshot, and indexes it in the database."""
        # Crawl URL content
        webpage = load_url(url)
        clean_title = re.sub(r'[\\/*?:"<>|]', "", webpage["title"])
        snapshot_filename = f"webpage_{clean_title[:30]}_{uuid.uuid4().hex[:6]}.txt"
        
        # Save raw webpage text snapshot persistently in local directory
        snapshot_path = os.path.join(URL_SNAPSHOTS_DIR, snapshot_filename)
        with open(snapshot_path, "w", encoding="utf-8") as f:
            f.write(f"Source URL: {url}\nTitle: {webpage['title']}\n\n{webpage['text']}")

        # Wrap text in page structure for text splitter
        pages = [{
            "page_number": 1,
            "text": webpage["text"]
        }]
        chunks = self.split_text_into_chunks(pages)
        
        # Use webpage title as document name
        doc_name = webpage["title"] if webpage["title"] else url

        metadata = self._resolve_metadata(metadata, pages, doc_name, "url")
        
        normalized_metadata = normalize_document_metadata(
            metadata=metadata,
            source_type="url",
            source_name=doc_name,
            source_info=url,
        )
        return self._index_chunks_in_qdrant(
            chunks,
            doc_name,
            "url",
            source_info=url,
            metadata=normalized_metadata,
        )

    def _index_chunks_in_qdrant(
        self,
        chunks: list[dict],
        doc_name: str,
        file_type: str,
        source_info: str = "",
        metadata: dict | None = None,
    ) -> dict:
        """Helper to batch embed and upsert chunks into local Qdrant collection."""
        self._delete_existing_document_points(doc_name, file_type, source_info)

        batch_size = 50
        texts_to_embed = [c["text"] for c in chunks]
        all_embeddings = []
        
        for i in range(0, len(texts_to_embed), batch_size):
            batch_texts = texts_to_embed[i:i + batch_size]
            embeddings = self.get_embeddings(batch_texts)
            all_embeddings.extend(embeddings)

        points = []
        for idx, chunk in enumerate(chunks):
            point_id = str(uuid.uuid4())
            payload = {
                "text": chunk["text"],
                "page_number": chunk["page_number"],
                "document_name": doc_name,
                "file_type": file_type,
                "source_info": source_info
            }
            if metadata:
                payload.update(metadata)

            points.append(
                PointStruct(
                    id=point_id,
                    vector=all_embeddings[idx],
                    payload=payload
                )
            )

        self.qdrant_client.upsert(
            collection_name=COLLECTION_NAME,
            points=points
        )
        return {
            "status": "success", 
            "message": f"Successfully indexed {doc_name}", 
            "chunks_count": len(chunks)
        }

    def _delete_existing_document_points(self, doc_name: str, file_type: str, source_info: str = "") -> None:
        """Remove existing chunks for a document before replacing its index entries."""
        if file_type == "url" and source_info:
            conditions = [
                FieldCondition(key="source_info", match=MatchValue(value=source_info))
            ]
        else:
            conditions = [
                FieldCondition(key="document_name", match=MatchValue(value=doc_name))
            ]

        self.qdrant_client.delete(
            collection_name=COLLECTION_NAME,
            points_selector=Filter(must=conditions),
            wait=True,
        )

    def _build_qdrant_filter(self, filters: QueryFilters | dict | None) -> Filter | None:
        normalized = normalize_query_filters(filters) if isinstance(filters, QueryFilters) or filters is None else filters
        if not normalized:
            return None

        conditions = []
        field_map = {
            "department": "department_key",
            "category": "category_key",
            "author": "author_key",
            "source_type": "file_type",
        }

        for filter_key, payload_key in field_map.items():
            value = normalized.get(filter_key)
            if value:
                conditions.append(FieldCondition(key=payload_key, match=MatchValue(value=value)))

        tags = normalized.get("tags") or []
        if tags:
            conditions.append(FieldCondition(key="tags_key", match=MatchAny(any=tags)))

        return Filter(must=conditions) if conditions else None

    def search_similar_chunks(self, query: str, limit: int = 5, filters: QueryFilters | None = None) -> list[dict]:
        """Search Qdrant for top matching chunks."""
        query_vector = self.get_query_embedding(query)
        query_filter = self._build_qdrant_filter(filters)
        
        response = self.qdrant_client.query_points(
            collection_name=COLLECTION_NAME,
            query=query_vector,
            limit=limit,
            query_filter=query_filter
        )
        
        matched_chunks = []
        for hit in response.points:
            matched_chunks.append({
                "score": hit.score,
                "text": hit.payload.get("text", ""),
                "page_number": hit.payload.get("page_number", 0),
                "document_name": hit.payload.get("document_name", "Unknown"),
                "file_type": hit.payload.get("file_type", "pdf"),
                "source_info": hit.payload.get("source_info", ""),
                "department": hit.payload.get("department"),
                "category": hit.payload.get("category"),
                "author": hit.payload.get("author"),
                "tags": hit.payload.get("tags", []),
                "uploaded_at": hit.payload.get("uploaded_at")
            })
        return matched_chunks

    def get_all_documents(self) -> list[dict]:
        """Retrieves list of unique documents indexed inside Qdrant."""
        try:
            scroll_results = self.qdrant_client.scroll(
                collection_name=COLLECTION_NAME,
                limit=1000,
                with_payload=True,
                with_vectors=False
            )
            
            records = scroll_results[0]
            unique_docs = {}
            for rec in records:
                doc_name = rec.payload.get("document_name")
                file_type = rec.payload.get("file_type", "pdf")
                if doc_name and doc_name not in unique_docs:
                    unique_docs[doc_name] = {
                        "name": doc_name,
                        "file_type": file_type,
                        "pages": set(),
                        "department": rec.payload.get("department"),
                        "category": rec.payload.get("category"),
                        "author": rec.payload.get("author"),
                        "tags": rec.payload.get("tags", []),
                        "uploaded_at": rec.payload.get("uploaded_at"),
                        "source_info": rec.payload.get("source_info", "")
                    }
                if doc_name:
                    unique_docs[doc_name]["pages"].add(rec.payload.get("page_number", 1))

            doc_list = []
            for doc_name, info in unique_docs.items():
                doc_list.append({
                    "name": doc_name,
                    "file_type": info["file_type"],
                    "total_pages": len(info["pages"]),
                    "department": info["department"],
                    "category": info["category"],
                    "author": info["author"],
                    "tags": info["tags"],
                    "uploaded_at": info["uploaded_at"],
                    "source_info": info["source_info"]
                })
            return doc_list
        except Exception as e:
            print(f"Error listing documents in services: {e}")
            return []

    def answer_query(self, query: str, filters: QueryFilters | None = None) -> dict:
        """RAG prompt compiler and generative answer generator."""
        if not GEMINI_API_KEY:
            return {
                "answer": "Error: GEMINI_API_KEY environment variable is not configured. Please set it in your environment.",
                "citations": []
            }

        citations = self.search_similar_chunks(query, limit=5, filters=filters)
        
        if not citations:
            return {
                "answer": "I couldn't find any documents in my knowledge base. Please upload a document or index a URL first.",
                "citations": []
            }

        # Build context prompt
        context_str = ""
        for idx, chunk in enumerate(citations):
            source_desc = f"Source {idx + 1}: {chunk['document_name']}"
            if chunk['file_type'] == 'url' and chunk['source_info']:
                source_desc += f" (URL: {chunk['source_info']})"
            else:
                source_desc += f" (Page {chunk['page_number']})"
            
            context_str += f"[{idx + 1}] {source_desc}\nContent: {chunk['text']}\n\n"

        system_instruction = (
            "You are ThinkStack, an AI-powered Enterprise Knowledge Management Assistant. "
            "You answer questions from employees using the provided context chunks of company documents.\n\n"
            "Strict Guidelines:\n"
            "- Answer the user's question accurately using ONLY the provided context snippets.\n"
            "- If the context doesn't contain the answer, say honestly that you cannot find the answer in the provided documents.\n"
            "- You MUST cite the source of any facts you state. Reference citations inline using numbers in brackets, e.g., 'Company leave policy allows 25 days off [1].' or 'Refer to the guidelines on page 3 [2].'\n"
            "- The numbers in brackets [N] MUST match the exact index of the provided context blocks."
        )

        prompt = f"""
System Instruction:
{system_instruction}

Context:
{context_str}

User Question: {query}

Answer:
"""
        try:
            model = genai.GenerativeModel("gemini-2.5-flash")
            response = model.generate_content(
                prompt,
                request_options={"timeout": GEMINI_REQUEST_TIMEOUT_SECONDS},
            )
            
            return {
                "answer": response.text,
                "citations": citations
            }
        except Exception as e:
            return {
                "answer": f"Error generating answer via Gemini API: {str(e)}",
                "citations": citations
            }
