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

# Set up storage and upload directories
qdrant_path = os.getenv("QDRANT_PATH", os.path.join("data", "qdrant"))
QDRANT_PATH = qdrant_path if os.path.isabs(qdrant_path) else os.path.join(backend_dir, qdrant_path)
UPLOADS_DIR = os.path.join(backend_dir, "uploads")
URL_SNAPSHOTS_DIR = os.path.join(UPLOADS_DIR, "url_snapshots")

# Ensure required directories are created automatically
os.makedirs(UPLOADS_DIR, exist_ok=True)
os.makedirs(URL_SNAPSHOTS_DIR, exist_ok=True)
os.makedirs(QDRANT_PATH, exist_ok=True)
