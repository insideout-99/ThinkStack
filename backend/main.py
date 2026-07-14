from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.endpoints import router
from app.config import CORS_ORIGINS, QDRANT_PATH
from app.db.session import create_tables, database_status

app = FastAPI(
    title="ThinkStack Enterprise RAG API", 
    version="2.0.0",
    description="AI-powered Knowledge Management Retrieval API"
)

# Setup CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register the API routes
app.include_router(router)


@app.on_event("startup")
def initialize_database():
    create_tables()
    status = database_status()
    if status["connected"]:
        print("ThinkStack startup: PostgreSQL is connected; operational history is enabled.")
    elif status["configured"]:
        print("ThinkStack startup: DATABASE_URL is configured but PostgreSQL is unavailable; running in vector-only mode.")
    else:
        print("ThinkStack startup: DATABASE_URL is not configured; running in vector-only mode.")
    print(f"ThinkStack startup: Qdrant local storage is {QDRANT_PATH}")

if __name__ == "__main__":
    import uvicorn
    # Start uvicorn server on port 8000
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)
