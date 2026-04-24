"""
query.py — Endpoint POST /query.

Recibe una consulta del usuario y devuelve la respuesta generada
por el pipeline RAG junto con las fuentes utilizadas.
"""

from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, HTTPException
from loguru import logger
from pydantic import BaseModel, field_validator

from api.services.query_service import run_query

router = APIRouter(tags=["query"])


# ─────────────────────────────────────────────────────────────
# Modelos de request/response
# ─────────────────────────────────────────────────────────────

class QueryRequest(BaseModel):
    """Solicitud de consulta al sistema RAG."""

    query: str
    filter_type: Optional[str] = None  # "github" | "web" | "document" | None

    @field_validator("query")
    @classmethod
    def validate_query(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("La consulta no puede estar vacía.")
        if len(v) > 2000:
            raise ValueError("La consulta no puede superar los 2000 caracteres.")
        return v.strip()

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "query": "¿Cómo funciona el sistema de autenticación?",
                    "filter_type": None,
                },
                {
                    "query": "¿Qué endpoints expone la API?",
                    "filter_type": "github",
                },
            ]
        }
    }


class SourceReference(BaseModel):
    """Referencia a una fuente utilizada en la respuesta."""
    file: str
    source: str
    type: str
    path: str
    score: float
    chunk_id: int


class QueryResponse(BaseModel):
    """Respuesta del sistema RAG con trazabilidad de fuentes."""
    answer: str
    sources: List[SourceReference]
    query: str
    model: str
    chunks_used: int


# ─────────────────────────────────────────────────────────────
# Endpoint
# ─────────────────────────────────────────────────────────────

@router.post(
    "/query",
    response_model=QueryResponse,
    summary="Consultar el sistema RAG",
)
async def query(request: QueryRequest) -> QueryResponse:
    """
    Ejecuta una consulta RAG sobre el contenido indexado.

    El proceso incluye:
    1. Vectorización de la consulta con SBERT.
    2. Recuperación de los chunks más relevantes desde Qdrant (top-k=5).
    3. Construcción del contexto y prompt controlado.
    4. Generación de respuesta con Qwen vía Ollama.
    5. Devolución de la respuesta con referencias a las fuentes.
    """
    logger.info(f"Query recibida: {request.query[:100]}...")

    try:
        result = run_query(
            query=request.query,
            filter_type=request.filter_type,
        )

        return QueryResponse(
            answer=result["answer"],
            sources=[SourceReference(**s) for s in result["sources"]],
            query=result["query"],
            model=result["model"],
            chunks_used=result["chunks_used"],
        )

    except Exception as e:
        logger.error(f"Error inesperado en /query: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error interno durante la consulta: {str(e)}",
        )
