"""
config.py — Configuración centralizada del sistema rag-rack.
Lee variables desde .env y las expone como un objeto Settings tipado.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    """Configuración global del sistema, cargada desde .env."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Qdrant
    qdrant_host: str = "qdrant"
    qdrant_port: int = 6333
    qdrant_collection: str = "rag_rack"

    # Ollama
    ollama_host: str = "ollama"
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
    frontend_api_url: str = "http://api:8000"

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
