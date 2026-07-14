import os
from dotenv import load_dotenv

# Calculate directory paths relative to this config file
# config.py is at: backend/app/config.py
# app_dir is at: backend/app/
# backend_dir is at: backend/
app_dir = os.path.dirname(__file__)
backend_dir = os.path.dirname(app_dir)

# Load environment variables from backend/.env
env_path = os.path.join(backend_dir, ".env")
load_dotenv(env_path)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
DATABASE_URL = os.getenv("DATABASE_URL")

# Keep uploads bounded before they are copied to disk. This can be overridden for
# legitimate large documents, but a positive value is always required.
MAX_UPLOAD_BYTES = int(os.getenv("MAX_UPLOAD_BYTES", str(25 * 1024 * 1024)))
if MAX_UPLOAD_BYTES <= 0:
    raise ValueError("MAX_UPLOAD_BYTES must be a positive integer.")

# Comma-separated origins. The local Vite server is the safe default; production
# deployments should set this explicitly rather than relying on a wildcard.
CORS_ORIGINS = [
    origin.strip()
    for origin in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")
    if origin.strip()
]
DATABASE_CONNECT_TIMEOUT_SECONDS = int(os.getenv("DATABASE_CONNECT_TIMEOUT_SECONDS", "3"))

# Set up storage and upload directories
qdrant_path = os.getenv("QDRANT_PATH", os.path.join("data", "qdrant"))
QDRANT_PATH = qdrant_path if os.path.isabs(qdrant_path) else os.path.join(backend_dir, qdrant_path)
UPLOADS_DIR = os.path.join(backend_dir, "uploads")
URL_SNAPSHOTS_DIR = os.path.join(UPLOADS_DIR, "url_snapshots")

# Ensure required directories are created automatically
os.makedirs(UPLOADS_DIR, exist_ok=True)
os.makedirs(URL_SNAPSHOTS_DIR, exist_ok=True)
os.makedirs(QDRANT_PATH, exist_ok=True)
