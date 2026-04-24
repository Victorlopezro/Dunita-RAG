"""
query_service.py — Servicio de consulta RAG.

Mantiene una instancia singleton del RAGPipeline y expone
la función de consulta para los endpoints de la API.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Optional

from loguru import logger

from api.config import get_settings
from api.pipelines.rag_pipeline import RAGPipeline, RAGResponse


@lru_cache(maxsize=1)
def get_rag_pipeline() -> RAGPipeline:
    """
    Devuelve la instancia singleton del RAGPipeline.
    Se inicializa una sola vez y se reutiliza en todas las consultas.
    """
    settings = get_settings()
    logger.info("Inicializando RAGPipeline singleton...")
    return RAGPipeline(
        qdrant_host=settings.qdrant_host,
        qdrant_port=settings.qdrant_port,
        qdrant_collection=settings.qdrant_collection,
        embedding_model_name=settings.embedding_model,
        embedding_dim=settings.embedding_dim,
        ollama_url=settings.ollama_url,
        ollama_model=settings.ollama_model,
        top_k=settings.top_k,
    )


def run_query(
    query: str,
    filter_type: Optional[str] = None,
) -> dict:
    """
    Ejecuta una consulta RAG y devuelve la respuesta con fuentes.

    Args:
        query: Pregunta del usuario.
        filter_type: Filtro opcional por tipo de fuente ("github", "web", "document").

    Returns:
        Dict con answer, sources, query, model y chunks_used.
    """
    if not query or not query.strip():
        return {
            "answer": "La consulta no puede estar vacía.",
            "sources": [],
            "query": query,
            "model": "",
            "chunks_used": 0,
        }

    pipeline = get_rag_pipeline()

    logger.info(f"Ejecutando query RAG: {query[:100]}...")
    response: RAGResponse = pipeline.run(
        query=query.strip(),
        filter_type=filter_type,
    )

    return {
        "answer": response.answer,
        "sources": response.sources,
        "query": response.query,
        "model": response.model,
        "chunks_used": response.chunks_used,
    }


def get_system_health() -> dict:
    """
    Verifica el estado de todos los componentes del sistema.

    Returns:
        Dict con estado de Qdrant, Ollama y el modelo de embeddings.
    """
    pipeline = get_rag_pipeline()
    return pipeline.health_check()
