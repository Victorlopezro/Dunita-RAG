"""
health.py — Endpoint GET /health.

Verifica el estado de todos los componentes del sistema:
Qdrant, Ollama y el modelo de embeddings.
"""

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from loguru import logger

from api.services.query_service import get_system_health

router = APIRouter(tags=["health"])


@router.get("/health", summary="Estado del sistema")
async def health_check() -> JSONResponse:
    """
    Verifica que todos los servicios del sistema están disponibles.

    Retorna:
    - **status**: "ok" si todos los componentes están operativos, "degraded" si alguno falla.
    - **components**: Estado individual de Qdrant, Ollama y el modelo de embeddings.
    """
    logger.info("Health check solicitado.")
    try:
        components = get_system_health()
        all_ok = all([
            components.get("qdrant", False),
            components.get("ollama", False),
            components.get("embedding_model", False),
        ])
        status_code = 200 if all_ok else 503
        return JSONResponse(
            status_code=status_code,
            content={
                "status": "ok" if all_ok else "degraded",
                "components": components,
            },
        )
    except Exception as e:
        logger.error(f"Error en health check: {e}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "error",
                "detail": str(e),
            },
        )
