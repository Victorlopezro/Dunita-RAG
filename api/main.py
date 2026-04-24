"""
main.py — Punto de entrada de la API FastAPI de rag-rack.

Registra los routers, configura el logging con loguru y
expone la aplicación para ser servida con uvicorn.
"""

import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from api.routes.health import router as health_router
from api.routes.ingest import router as ingest_router
from api.routes.query import router as query_router


# ─────────────────────────────────────────────────────────────
# Configuración de logging
# ─────────────────────────────────────────────────────────────

logger.remove()
logger.add(
    sys.stdout,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{line}</cyan> — <level>{message}</level>",
    level="INFO",
    colorize=True,
)
logger.add(
    "/tmp/rag_rack_api.log",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{line} — {message}",
    level="DEBUG",
    rotation="10 MB",
    retention="7 days",
)


# ─────────────────────────────────────────────────────────────
# Lifecycle
# ─────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Inicialización y limpieza al arrancar/detener la API."""
    logger.info("=" * 60)
    logger.info("rag-rack API iniciando...")
    logger.info("=" * 60)

    # Pre-cargar el modelo de embeddings al arrancar
    try:
        from api.config import get_settings
        from ingest.embedding import get_embedding_model
        settings = get_settings()
        model = get_embedding_model(settings.embedding_model)
        logger.info(f"Modelo de embeddings cargado: {settings.embedding_model} (dim={model.dimension})")
    except Exception as e:
        logger.warning(f"No se pudo pre-cargar el modelo de embeddings: {e}")

    yield

    logger.info("rag-rack API detenida.")


# ─────────────────────────────────────────────────────────────
# Aplicación FastAPI
# ─────────────────────────────────────────────────────────────

app = FastAPI(
    title="rag-rack API",
    description=(
        "API del sistema RAG rag-rack. "
        "Permite ingestar repositorios GitHub, páginas web y documentos, "
        "y consultarlos mediante un pipeline RAG con Qwen + Haystack + Qdrant."
    ),
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS — permite peticiones desde el frontend Streamlit
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Registrar routers
app.include_router(health_router)
app.include_router(ingest_router)
app.include_router(query_router)


@app.get("/", include_in_schema=False)
async def root():
    return {
        "service": "rag-rack API",
        "version": "1.0.0",
        "docs": "/docs",
    }


# ─────────────────────────────────────────────────────────────
# Entrada directa (desarrollo local)
# ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    from api.config import get_settings

    settings = get_settings()
    uvicorn.run(
        "api.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=True,
        log_level="info",
    )
