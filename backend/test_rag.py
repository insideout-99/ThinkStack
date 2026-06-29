import os
from app.services.rag_service import RAGService

def test_chunking():
    print("Testing text chunking...")
    service = RAGService.__new__(RAGService)
    pages = [
        {
            "page_number": 1,
            "text": "This is page 1 of the employee handbook. The leave policy dictates that employees get 25 days of paid time off per calendar year. This must be requested 2 weeks in advance."
        },
        {
            "page_number": 2,
            "text": "This is page 2. Regarding payment, payments are processed on the 25th of every month. If the 25th falls on a weekend, it will be paid on the preceding Friday."
        }
    ]
    chunks = service.split_text_into_chunks(pages, chunk_size=100, chunk_overlap=20)
    print(f"Total chunks created: {len(chunks)}")
    for i, c in enumerate(chunks):
        print(f"Chunk {i+1} (Page {c['page_number']}): {c['text']}")
    assert len(chunks) > 0, "Failed to create chunks."
    print("Chunking test passed!\n")

def test_full_rag():
    # Only run if API key is present
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("GEMINI_API_KEY is not set in environment. Skipping RAG integration test.")
        print("To test, set GEMINI_API_KEY in backend/.env or your terminal session.")
        return
        
    try:
        print("Running integration RAG test using Gemini...")
        service = RAGService()

        # We will test search and answer on existing database.
        # Ingest handbook.pdf if not already indexed
        if not os.path.exists("handbook.pdf"):
            print("ERROR: handbook.pdf not found!")
            return
        print("Indexing handbook.pdf...")
        ingest_res = service.ingest_file("handbook.pdf", "handbook.pdf")
        print(f"Ingestion result: {ingest_res}")
        
        docs = service.get_all_documents()
        print(f"Ingested documents: {docs}")
        
        # Test query
        test_query = "What is the leave policy?"
        print(f"Querying: '{test_query}'")
        res = service.answer_query(test_query)
        print("Answer:")
        print(res.get("answer"))
        print("\nCitations:")
        for cit in res.get("citations", []):
            print(f"- {cit['document_name']} (Page {cit['page_number']}) - Score: {cit['score']}")
    except Exception as e:
        print(f"RAG integration failed: {e}")

if __name__ == "__main__":
    print("Starting ThinkStack RAG Backend tests...\n")
    test_chunking()
    test_full_rag()
    print("Tests finished.")
