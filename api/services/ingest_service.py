"""
ingest_service.py — Servicio de ingesta multifuente.

Orquesta los workers de ingesta (GitHub, Web, Docling) y el pipeline
de chunking + embedding + indexación en Qdrant.

Este servicio es el punto de entrada para todos los flujos de ingesta,
manteniendo la lógica fuera de los endpoints de la API.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path
from typing import List

from loguru import logger

from api.config import get_settings
from ingest.chunking import chunk_text
from ingest.embedding import get_embedding_model
from ingest.indexer import QdrantIndexer


def _get_indexer() -> QdrantIndexer:
    """Crea una instancia de QdrantIndexer con la configuración actual."""
    settings = get_settings()
    return QdrantIndexer(
        host=settings.qdrant_host,
        port=settings.qdrant_port,
        collection=settings.qdrant_collection,
        embedding_dim=settings.embedding_dim,
    )


def _process_documents(documents: List[dict]) -> dict:
    """
    Procesa una lista de documentos (resultado de cualquier worker):
    chunking → embedding → indexación.

    Args:
        documents: Lista de dicts con keys: source, type, path, file, content.

    Returns:
        Dict con estadísticas de la ingesta.
    """
    settings = get_settings()
    embedding_model = get_embedding_model(settings.embedding_model)
    indexer = _get_indexer()
    indexer.ensure_collection()

    now = datetime.now(timezone.utc).isoformat()
    total_chunks = 0
    total_docs = 0
    errors = []

    for doc in documents:
        try:
            chunks = chunk_text(
                text=doc["content"],
                source=doc["source"],
                doc_type=doc["type"],
                path=doc["path"],
                file=doc["file"],
                ingested_at=now,
                chunk_size=settings.chunk_size,
                chunk_overlap=settings.chunk_overlap,
            )

            if not chunks:
                logger.warning(f"Sin chunks para: {doc['file']}")
                continue

            indexed = indexer.index_chunks(chunks, embedding_model)
            total_chunks += indexed
            total_docs += 1

        except Exception as e:
            error_msg = f"Error procesando {doc.get('file', 'unknown')}: {e}"
            logger.error(error_msg)
            errors.append(error_msg)

    return {
        "documents_processed": total_docs,
        "chunks_indexed": total_chunks,
        "errors": errors,
    }


def ingest_github(repo_urls: List[str]) -> dict:
    """
    Ingesta uno o más repositorios GitHub.

    Args:
        repo_urls: Lista de URLs de repositorios.

    Returns:
        Dict con estadísticas de la ingesta.
    """
    from ingest.github_worker import ingest_github_repo

    if not repo_urls:
        return {"error": "No se proporcionaron URLs de repositorios."}

    all_documents = []
    repo_errors = []

    for url in repo_urls:
        logger.info(f"Iniciando ingesta de repo: {url}")
        try:
            docs = ingest_github_repo(url)
            all_documents.extend(docs)
            logger.info(f"Repo {url}: {len(docs)} archivos extraídos.")
        except Exception as e:
            error_msg = f"Error clonando {url}: {e}"
            logger.error(error_msg)
            repo_errors.append(error_msg)

    result = _process_documents(all_documents)
    result["repos_attempted"] = len(repo_urls)
    result["repo_errors"] = repo_errors
    return result


def ingest_web(urls: List[str]) -> dict:
    """
    Ingesta una lista de páginas web.

    Args:
        urls: Lista de URLs a rastrear.

    Returns:
        Dict con estadísticas de la ingesta.
    """
    from ingest.crawl4ai_worker import ingest_web_urls

    if not urls:
        return {"error": "No se proporcionaron URLs."}

    logger.info(f"Iniciando ingesta web de {len(urls)} URLs...")
    documents = ingest_web_urls(urls)
    result = _process_documents(documents)
    result["urls_attempted"] = len(urls)
    return result


def ingest_documents_from_paths(file_paths: List[str]) -> dict:
    """
    Ingesta documentos desde rutas de archivo locales.

    Args:
        file_paths: Lista de rutas a archivos (PDF, DOCX, etc.).

    Returns:
        Dict con estadísticas de la ingesta.
    """
    from ingest.docling_worker import ingest_documents

    if not file_paths:
        return {"error": "No se proporcionaron rutas de archivos."}

    logger.info(f"Iniciando ingesta documental de {len(file_paths)} archivos...")
    documents = ingest_documents(file_paths)
    result = _process_documents(documents)
    result["files_attempted"] = len(file_paths)
    return result
