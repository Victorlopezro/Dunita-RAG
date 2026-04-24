"""
create_collection.py — Crea la colección vectorial en Qdrant.

Uso:
    python scripts/create_collection.py

Verifica también que Ollama está disponible y tiene el modelo descargado.
Si el modelo no está disponible, lo descarga automáticamente.
"""

import sys
import os

# Asegurar que el directorio raíz está en el path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import httpx
from loguru import logger
from dotenv import load_dotenv

load_dotenv()

from api.config import get_settings
from ingest.indexer import QdrantIndexer


def check_qdrant(settings) -> bool:
    """Verifica que Qdrant está disponible."""
    try:
        resp = httpx.get(f"{settings.qdrant_url}/healthz", timeout=10)
        resp.raise_for_status()
        logger.info(f"✅ Qdrant disponible en {settings.qdrant_url}")
        return True
    except Exception as e:
        logger.error(f"❌ Qdrant no disponible: {e}")
        return False


def check_ollama(settings) -> bool:
    """Verifica que Ollama está disponible y tiene el modelo."""
    try:
        resp = httpx.get(f"{settings.ollama_url}/api/tags", timeout=10)
        resp.raise_for_status()
        models = [m["name"] for m in resp.json().get("models", [])]
        logger.info(f"✅ Ollama disponible. Modelos: {models}")

        # Verificar si el modelo está disponible
        model_available = any(settings.ollama_model in m for m in models)
        if not model_available:
            logger.warning(
                f"⚠️  Modelo '{settings.ollama_model}' no encontrado. "
                f"Descargando..."
            )
            pull_model(settings)
        else:
            logger.info(f"✅ Modelo '{settings.ollama_model}' disponible.")
        return True
    except Exception as e:
        logger.error(f"❌ Ollama no disponible: {e}")
        return False


def pull_model(settings) -> None:
    """Descarga el modelo en Ollama."""
    logger.info(f"Descargando modelo: {settings.ollama_model}")
    try:
        resp = httpx.post(
            f"{settings.ollama_url}/api/pull",
            json={"name": settings.ollama_model, "stream": False},
            timeout=600,
        )
        resp.raise_for_status()
        logger.info(f"✅ Modelo '{settings.ollama_model}' descargado correctamente.")
    except Exception as e:
        logger.error(f"❌ Error descargando modelo: {e}")
        raise


def create_collection(settings) -> None:
    """Crea la colección en Qdrant si no existe."""
    indexer = QdrantIndexer(
        host=settings.qdrant_host,
        port=settings.qdrant_port,
        collection=settings.qdrant_collection,
        embedding_dim=settings.embedding_dim,
    )
    indexer.ensure_collection()
    info = indexer.collection_info()
    logger.info(f"✅ Colección '{settings.qdrant_collection}': {info}")


def main():
    settings = get_settings()
    logger.info("=" * 50)
    logger.info("rag-rack — Inicialización del sistema")
    logger.info("=" * 50)
    logger.info(f"Qdrant URL: {settings.qdrant_url}")
    logger.info(f"Ollama URL: {settings.ollama_url}")
    logger.info(f"Modelo LLM: {settings.ollama_model}")
    logger.info(f"Modelo embeddings: {settings.embedding_model} (dim={settings.embedding_dim})")
    logger.info(f"Colección: {settings.qdrant_collection}")
    logger.info("=" * 50)

    errors = []

    if not check_qdrant(settings):
        errors.append("Qdrant no disponible")

    if not check_ollama(settings):
        errors.append("Ollama no disponible")

    if errors:
        logger.error(f"Errores encontrados: {errors}")
        logger.error("Asegúrate de que los servicios están corriendo: docker compose up -d qdrant ollama")
        sys.exit(1)

    create_collection(settings)

    logger.info("=" * 50)
    logger.info("✅ Sistema inicializado correctamente.")
    logger.info("Ahora puedes ejecutar: docker compose up -d api frontend")
    logger.info("=" * 50)


if __name__ == "__main__":
    main()
