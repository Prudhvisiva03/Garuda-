import os
from pathlib import Path
from pydantic_settings import BaseSettings

# Base directory for the backend
BASE_DIR = Path(__file__).resolve().parent.parent

class Settings(BaseSettings):
    APP_NAME: str = "EviSutra Forensics Engine"
    API_V1_STR: str = "/api/v1"
    VERSION: str = "0.2.0-alpha"
    
    # Storage paths
    STORAGE_DIR: Path = BASE_DIR / "storage"
    EVIDENCE_DIR: Path = STORAGE_DIR / "evidence"
    ARTIFACTS_DIR: Path = STORAGE_DIR / "artifacts"
    REPORTS_DIR: Path = STORAGE_DIR / "reports"
    DB_PATH: Path = STORAGE_DIR / "evisutra.db"
    
    # Upload limits & constraints
    MAX_UPLOAD_SIZE: int = 10 * 1024 * 1024  # 10 MiB limit
    MAX_IMAGE_PIXELS: int = 50_000_000      # 50 Megapixels max (decompression bomb protection)
    ALLOWED_EXTENSIONS: set[str] = {".jpg", ".jpeg", ".png"}
    ALLOWED_MIME_TYPES: set[str] = {"image/jpeg", "image/png"}
    
    # Analysis defaults
    DEFAULT_ELA_QUALITY: int = 95
    DEFAULT_ELA_SCALE: int = 15
    
    # CORS origins
    CORS_ORIGINS: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]

    model_config = {"env_prefix": "EVISUTRA_"}

settings = Settings()

# Ensure directories exist
settings.STORAGE_DIR.mkdir(parents=True, exist_ok=True)
settings.EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
settings.ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
settings.REPORTS_DIR.mkdir(parents=True, exist_ok=True)
