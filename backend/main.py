from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.endpoints import router
from app.db.session import create_tables

app = FastAPI(
    title="ThinkStack Enterprise RAG API", 
    version="2.0.0",
    description="AI-powered Knowledge Management Retrieval API"
)

# Setup CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict to frontend origin http://localhost:5173 in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register the API routes
app.include_router(router)


@app.on_event("startup")
def initialize_database():
    create_tables()

if __name__ == "__main__":
    import uvicorn
    # Start uvicorn server on port 8000
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)
