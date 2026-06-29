import os
import uuid
import shutil
import re
import google.generativeai as genai
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, FieldCondition, Filter, MatchValue, PointStruct, VectorParams

# Import configurations
from app.config import GEMINI_API_KEY, QDRANT_PATH, UPLOADS_DIR, URL_SNAPSHOTS_DIR
# Import loaders
from app.services.document_loaders import load_pdf, load_docx, load_text_or_md, load_url

COLLECTION_NAME = "thinkstack_documents"

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
            
        try:
            result = genai.embed_content(
                model="models/gemini-embedding-001",
                content=texts,
                task_type="retrieval_document",
                output_dimensionality=768
            )
            return result["embedding"]
        except Exception as e:
            raise RuntimeError(f"Error generating embeddings via Gemini API: {str(e)}")

    def get_query_embedding(self, query: str) -> list[float]:
        """Generates embedding for a search query."""
        if not GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY environment variable is not set in backend/.env")
            
        try:
            result = genai.embed_content(
                model="models/gemini-embedding-001",
                content=query,
                task_type="retrieval_query",
                output_dimensionality=768
            )
            return result["embedding"]
        except Exception as e:
            raise RuntimeError(f"Error generating query embedding: {str(e)}")

    def ingest_file(self, source_path: str, original_filename: str) -> dict:
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

        # Index chunks in Qdrant. Existing points for the same file are removed first
        # so re-uploading a file replaces stale content instead of duplicating it.
        return self._index_chunks_in_qdrant(chunks, original_filename, file_type, source_info=dest_path)

    def ingest_url(self, url: str) -> dict:
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
        
        return self._index_chunks_in_qdrant(chunks, doc_name, "url", source_info=url)

    def _index_chunks_in_qdrant(self, chunks: list[dict], doc_name: str, file_type: str, source_info: str = "") -> dict:
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
            points.append(
                PointStruct(
                    id=point_id,
                    vector=all_embeddings[idx],
                    payload={
                        "text": chunk["text"],
                        "page_number": chunk["page_number"],
                        "document_name": doc_name,
                        "file_type": file_type,
                        "source_info": source_info
                    }
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

    def search_similar_chunks(self, query: str, limit: int = 5) -> list[dict]:
        """Search Qdrant for top matching chunks."""
        query_vector = self.get_query_embedding(query)
        
        response = self.qdrant_client.query_points(
            collection_name=COLLECTION_NAME,
            query=query_vector,
            limit=limit
        )
        
        matched_chunks = []
        for hit in response.points:
            matched_chunks.append({
                "score": hit.score,
                "text": hit.payload.get("text", ""),
                "page_number": hit.payload.get("page_number", 0),
                "document_name": hit.payload.get("document_name", "Unknown"),
                "file_type": hit.payload.get("file_type", "pdf"),
                "source_info": hit.payload.get("source_info", "")
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
                        "pages": set()
                    }
                if doc_name:
                    unique_docs[doc_name]["pages"].add(rec.payload.get("page_number", 1))

            doc_list = []
            for doc_name, info in unique_docs.items():
                doc_list.append({
                    "name": doc_name,
                    "file_type": info["file_type"],
                    "total_pages": len(info["pages"])
                })
            return doc_list
        except Exception as e:
            print(f"Error listing documents in services: {e}")
            return []

    def answer_query(self, query: str) -> dict:
        """RAG prompt compiler and generative answer generator."""
        if not GEMINI_API_KEY:
            return {
                "answer": "Error: GEMINI_API_KEY environment variable is not configured. Please set it in your environment.",
                "citations": []
            }

        citations = self.search_similar_chunks(query, limit=5)
        
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
            response = model.generate_content(prompt)
            
            return {
                "answer": response.text,
                "citations": citations
            }
        except Exception as e:
            return {
                "answer": f"Error generating answer via Gemini API: {str(e)}",
                "citations": citations
            }
