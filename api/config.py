"""
config.py - Configuracion centralizada del sistema rag-rack.

Usa ruta absoluta para encontrar el .env independientemente
del directorio de trabajo. Funciona en Docker y Windows sin Docker.
"""
import os
from pathlib import Path
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

# Ruta absoluta al directorio raiz del proyecto
# api/config.py -> api/ -> proyecto/
_PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Buscar .env por ruta absoluta (no depende del cwd)
_ENV_FILE = _PROJECT_ROOT / ".env"
if not _ENV_FILE.exists():
    _ENV_WINDOWS = _PROJECT_ROOT / "env_windows.txt"
    if _ENV_WINDOWS.exists():
        _ENV_FILE = _ENV_WINDOWS


class Settings(BaseSettings):
    """Configuracion global del sistema, cargada desde .env."""

    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Qdrant — default "localhost" para modo sin Docker
    qdrant_host: str = "localhost"
    qdrant_port: int = 6333
    qdrant_collection: str = "rag_rack"

    # Ollama
    ollama_host: str = "localhost"
    ollama_port: int = 11434
    ollama_model: str = "qwen2.5:7b"

    # Embeddings
    embedding_model: str = "all-MiniLM-L6-v2"
    embedding_dim: int = 384

    # Chunking
    chunk_size: int = 600
    chunk_overlap: int = 75

    # RAG retrieval
    top_k: int = 5

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    # Frontend
    frontend_api_url: str = "http://localhost:8000"

    @property
    def qdrant_url(self) -> str:
        return f"http://{self.qdrant_host}:{self.qdrant_port}"

    @property
    def ollama_url(self) -> str:
        return f"http://{self.ollama_host}:{self.ollama_port}"


@lru_cache
def get_settings() -> Settings:
    """Devuelve la instancia singleton de Settings (cacheada)."""
    return Settings()
