"""
ingest.py — Endpoint POST /ingest.

Acepta solicitudes de ingesta para tres tipos de fuente:
- github: Lista de URLs de repositorios GitHub.
- web: Lista de URLs de páginas web.
- document: Lista de rutas de archivos locales.
"""

from __future__ import annotations
import os

from enum import Enum
from typing import List, Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException
from loguru import logger
from pydantic import BaseModel, field_validator

router = APIRouter(tags=["ingest"])


# ─────────────────────────────────────────────────────────────
# Modelos de request/response
# ─────────────────────────────────────────────────────────────

class SourceType(str, Enum):
    github = "github"
    web = "web"
    document = "document"


class IngestRequest(BaseModel):
    """Solicitud de ingesta de contenido."""

    source_type: SourceType
    urls: Optional[List[str]] = None          # Para github y web
    file_paths: Optional[List[str]] = None    # Para document

    @field_validator("urls")
    @classmethod
    def validate_urls(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        if v is not None:
            cleaned = [url.strip() for url in v if url.strip()]
            if not cleaned:
                raise ValueError("La lista de URLs no puede estar vacía.")
            return cleaned
        return v

    @field_validator("file_paths")
    @classmethod
    def validate_file_paths(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        if v is not None:
            cleaned = [p.strip() for p in v if p.strip()]
            if not cleaned:
                raise ValueError("La lista de rutas no puede estar vacía.")
            return cleaned
        return v

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "source_type": "github",
                    "urls": ["https://github.com/usuario/repositorio"],
                },
                {
                    "source_type": "web",
                    "urls": ["https://ejemplo.com/docs", "https://ejemplo.com/api"],
                },
                {
                    "source_type": "document",
                    "file_paths": ["/data/raw/documento.pdf"],
                },
            ]
        }
    }


class IngestResponse(BaseModel):
    """Respuesta de la operación de ingesta."""
    status: str
    source_type: str
    documents_processed: int = 0
    chunks_indexed: int = 0
    errors: List[str] = []
    detail: Optional[str] = None


# ─────────────────────────────────────────────────────────────
# Endpoint
# ─────────────────────────────────────────────────────────────

@router.post(
    "/ingest",
    response_model=IngestResponse,
    summary="Ingestar contenido en el índice vectorial",
)
async def ingest(request: IngestRequest) -> IngestResponse:
    """
    Ingesta contenido desde GitHub, páginas web o documentos locales.

    El proceso incluye:
    1. Extracción del contenido según el tipo de fuente.
    2. Chunking con overlap.
    3. Generación de embeddings con SBERT.
    4. Indexación en Qdrant con metadatos de trazabilidad.
    """
    logger.info(f"Solicitud de ingesta recibida: type={request.source_type}")

    try:
        if request.source_type == SourceType.github:
            if not request.urls:
                raise HTTPException(
                    status_code=422,
                    detail="Se requiere 'urls' para ingesta de tipo 'github'.",
                )
            from api.services.ingest_service import ingest_github
            result = ingest_github(request.urls)

        elif request.source_type == SourceType.web:
            if not request.urls:
                raise HTTPException(
                    status_code=422,
                    detail="Se requiere 'urls' para ingesta de tipo 'web'.",
                )
            from api.services.ingest_service import ingest_web
            result = ingest_web(request.urls)

        elif request.source_type == SourceType.document:
            if not request.file_paths:
                raise HTTPException(
                    status_code=422,
                    detail="Se requiere 'file_paths' para ingesta de tipo 'document'.",
                )
            from api.services.ingest_service import ingest_documents_from_paths
            result = ingest_documents_from_paths(request.file_paths)

        else:
            raise HTTPException(status_code=400, detail="Tipo de fuente no válido.")

        if "error" in result:
            return IngestResponse(
                status="error",
                source_type=request.source_type,
                detail=result["error"],
            )

        return IngestResponse(
            status="success",
            source_type=request.source_type,
            documents_processed=result.get("documents_processed", 0),
            chunks_indexed=result.get("chunks_indexed", 0),
            errors=result.get("errors", []),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error inesperado en /ingest: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error interno durante la ingesta: {str(e)}",
        )


# ─────────────────────────────────────────────────────────────
# Endpoint de subida de archivos (multipart/form-data)
# ─────────────────────────────────────────────────────────────
from fastapi import UploadFile, File
import tempfile
import shutil

@router.post(
    "/ingest/upload",
    response_model=IngestResponse,
    summary="Subir y procesar documentos directamente",
)
async def ingest_upload(files: List[UploadFile] = File(...)) -> IngestResponse:
    """
    Sube uno o varios archivos (PDF, DOCX, PPTX, XLSX, MD, TXT)
    y los ingesta directamente en el índice vectorial.
    """
    logger.info(f"Subida de {len(files)} archivo(s) para ingesta.")
    tmp_dir = tempfile.mkdtemp(prefix="rag_upload_")
    saved_paths = []
    try:
        for upload in files:
            dest = os.path.join(tmp_dir, upload.filename)
            with open(dest, "wb") as f:
                shutil.copyfileobj(upload.file, f)
            saved_paths.append(dest)
            logger.info(f"Archivo guardado temporalmente: {dest}")

        from api.services.ingest_service import ingest_documents_from_paths
        result = ingest_documents_from_paths(saved_paths)

        if "error" in result:
            return IngestResponse(
                status="error",
                source_type="document",
                detail=result["error"],
            )
        return IngestResponse(
            status="success",
            source_type="document",
            documents_processed=result.get("documents_processed", 0),
            chunks_indexed=result.get("chunks_indexed", 0),
            errors=result.get("errors", []),
        )
    except Exception as e:
        logger.error(f"Error en /ingest/upload: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error durante la subida: {str(e)}")
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)
