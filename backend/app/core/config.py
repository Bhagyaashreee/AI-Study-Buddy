from pathlib import Path
from typing import List, Union
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


# Project Root Directory calculation
# This file is located at <project_root>/backend/app/core/config.py
CORE_DIR = Path(__file__).resolve().parent
APP_DIR = CORE_DIR.parent
BACKEND_DIR = APP_DIR.parent
PROJECT_ROOT = BACKEND_DIR.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # Application Information
    PROJECT_NAME: str = "AI Study Buddy"
    PROJECT_VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"

    # Server Settings
    HOST: str = "127.0.0.1"
    PORT: int = 8000

    # Ollama Local AI (Strictly zero-cost local inference)
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3.2:3b"
    OLLAMA_TIMEOUT_SECONDS: float = 120.0
    OLLAMA_KEEP_ALIVE: str = "30m"

    # Free Local Embedding Model (Runs locally via sentence-transformers)
    EMBEDDING_MODEL_NAME: str = "all-MiniLM-L6-v2"
    EMBEDDING_DIMENSION: int = 384

    # Document Upload & Chunking Configuration
    MAX_UPLOAD_SIZE_BYTES: int = 50 * 1024 * 1024  # 50 MB
    CHUNK_SIZE: int = 600
    CHUNK_OVERLAP: int = 100

    # Retrieval-Augmented Generation (RAG) Settings
    RAG_TOP_K: int = 4
    RAG_SIMILARITY_THRESHOLD: float = 0.12

    # SQLite Database Configuration
    DATABASE_URL: str = f"sqlite:///{PROJECT_ROOT.as_posix()}/data/study_buddy.db"

    # Storage Directories
    DATA_DIR: Path = PROJECT_ROOT / "data"
    UPLOAD_DIR: Path = PROJECT_ROOT / "data" / "uploads"
    VECTOR_DIR: Path = PROJECT_ROOT / "data" / "vectorstore"

    # CORS Origins (For local frontend development)
    CORS_ORIGINS: Union[str, List[str]] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000"
    ]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        elif isinstance(v, list):
            return v
        return ["http://localhost:5173", "http://127.0.0.1:5173"]

    def ensure_directories_exist(self) -> None:
        """Create storage directories if they do not exist."""
        self.DATA_DIR.mkdir(parents=True, exist_ok=True)
        self.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        self.VECTOR_DIR.mkdir(parents=True, exist_ok=True)


settings = Settings()
settings.ensure_directories_exist()
