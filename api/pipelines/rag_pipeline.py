"""
rag_pipeline.py — Pipeline RAG principal usando Haystack 2.x.

Flujo del pipeline:
1. Embed de la consulta con SBERT.
2. Recuperación de top-k chunks desde Qdrant.
3. Construcción del contexto y prompt controlado.
4. Generación de respuesta con Qwen vía Ollama.
5. Devolución de respuesta + fuentes (trazabilidad).

Nota: Se implementa como pipeline Haystack 2.x con componentes
personalizados para Qdrant y Ollama, ya que la integración oficial
de Haystack con Qdrant requiere configuración específica.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

import httpx
from loguru import logger

from ingest.embedding import EmbeddingModel, get_embedding_model
from ingest.indexer import QdrantIndexer


# ─────────────────────────────────────────────────────────────
# Modelos de datos
# ─────────────────────────────────────────────────────────────

@dataclass
class RetrievedChunk:
    """Chunk recuperado de Qdrant con su score de relevancia."""
    text: str
    score: float
    source: str
    type: str
    path: str
    file: str
    chunk_id: int


@dataclass
class RAGResponse:
    """Respuesta completa del pipeline RAG con trazabilidad."""
    answer: str
    sources: List[dict] = field(default_factory=list)
    query: str = ""
    model: str = ""
    chunks_used: int = 0


# ─────────────────────────────────────────────────────────────
# Componentes del pipeline
# ─────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """Eres un asistente técnico especializado en responder preguntas
basándote EXCLUSIVAMENTE en el contexto proporcionado.

Reglas:
- Responde SOLO con información presente en el contexto.
- Si la información no está en el contexto, di claramente: "No tengo información suficiente en los documentos indexados para responder esta pregunta."
- Cita las fuentes cuando sea relevante.
- Responde en el mismo idioma que la pregunta.
- Sé conciso y preciso."""


def build_context(chunks: List[RetrievedChunk]) -> str:
    """
    Construye el string de contexto a partir de los chunks recuperados.
    Incluye metadatos de fuente para trazabilidad.
    """
    parts = []
    for i, chunk in enumerate(chunks, 1):
        source_info = f"[Fuente {i}: {chunk.file} ({chunk.source})]"
        parts.append(f"{source_info}\n{chunk.text}")
    return "\n\n---\n\n".join(parts)


def build_prompt(query: str, context: str) -> str:
    """
    Construye el prompt final para el LLM.
    Formato: contexto + pregunta del usuario.
    """
    return f"""CONTEXTO RECUPERADO:
{context}

---

PREGUNTA: {query}

RESPUESTA:"""


def retrieve_chunks(
    query: str,
    indexer: QdrantIndexer,
    embedding_model: EmbeddingModel,
    top_k: int = 5,
    filter_type: str | None = None,
) -> List[RetrievedChunk]:
    """
    Genera el embedding de la consulta y recupera los chunks más relevantes.

    Args:
        query: Consulta del usuario.
        indexer: Instancia de QdrantIndexer.
        embedding_model: Modelo SBERT.
        top_k: Número de chunks a recuperar.
        filter_type: Filtro opcional por tipo de fuente.

    Returns:
        Lista de RetrievedChunk ordenados por relevancia.
    """
    logger.debug(f"Generando embedding para query: {query[:80]}...")
    query_vector = embedding_model.embed_single(query)

    logger.debug(f"Buscando top-{top_k} chunks en Qdrant...")
    raw_results = indexer.search(
        query_vector=query_vector,
        top_k=top_k,
        filter_type=filter_type,
    )

    chunks = [
        RetrievedChunk(
            text=r["text"],
            score=r["score"],
            source=r["source"],
            type=r["type"],
            path=r["path"],
            file=r["file"],
            chunk_id=r["chunk_id"],
        )
        for r in raw_results
    ]

    logger.debug(f"Recuperados {len(chunks)} chunks (scores: {[f'{c.score:.3f}' for c in chunks]})")
    return chunks


def generate_with_ollama(
    prompt: str,
    ollama_url: str,
    model: str,
    system_prompt: str = SYSTEM_PROMPT,
    temperature: float = 0.1,
    timeout: int = 120,
) -> str:
    """
    Genera una respuesta usando Ollama (API compatible con OpenAI).

    Args:
        prompt: Prompt con contexto y pregunta.
        ollama_url: URL base de Ollama (ej: http://ollama:11434).
        model: Nombre del modelo (ej: qwen2.5:7b).
        system_prompt: Instrucciones del sistema.
        temperature: Temperatura de generación (bajo = más determinista).
        timeout: Timeout en segundos.

    Returns:
        Texto de la respuesta generada.
    """
    url = f"{ollama_url}/api/chat"
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ],
        "stream": False,
        "options": {
            "temperature": temperature,
            "num_predict": 1024,
        },
    }

    logger.debug(f"Enviando prompt a Ollama ({model})...")
    try:
        response = httpx.post(url, json=payload, timeout=timeout)
        response.raise_for_status()
        data = response.json()
        answer = data["message"]["content"].strip()
        logger.debug(f"Respuesta recibida de Ollama ({len(answer)} chars)")
        return answer
    except httpx.TimeoutException:
        raise RuntimeError(f"Timeout esperando respuesta de Ollama ({timeout}s)")
    except httpx.HTTPStatusError as e:
        raise RuntimeError(f"Error HTTP de Ollama: {e.response.status_code} — {e.response.text}")
    except Exception as e:
        raise RuntimeError(f"Error inesperado con Ollama: {e}")


# ─────────────────────────────────────────────────────────────
# Pipeline principal
# ─────────────────────────────────────────────────────────────

class RAGPipeline:
    """
    Pipeline RAG completo: retrieval + generation con trazabilidad.

    Orquesta los componentes de forma modular:
    - EmbeddingModel (SBERT) para vectorizar queries
    - QdrantIndexer para recuperar chunks relevantes
    - Ollama/Qwen para generar la respuesta final
    """

    def __init__(
        self,
        qdrant_host: str = "localhost",
        qdrant_port: int = 6333,
        qdrant_collection: str = "rag_rack",
        embedding_model_name: str = "all-MiniLM-L6-v2",
        embedding_dim: int = 384,
        ollama_url: str = "http://localhost:11434",
        ollama_model: str = "qwen2.5:7b",
        top_k: int = 5,
    ):
        self.ollama_url = ollama_url
        self.ollama_model = ollama_model
        self.top_k = top_k

        # Inicializar componentes
        self.embedding_model = get_embedding_model(embedding_model_name)
        self.indexer = QdrantIndexer(
            host=qdrant_host,
            port=qdrant_port,
            collection=qdrant_collection,
            embedding_dim=embedding_dim,
        )

        logger.info(
            f"RAGPipeline inicializado: model={ollama_model}, "
            f"top_k={top_k}, collection={qdrant_collection}"
        )

    def run(
        self,
        query: str,
        filter_type: str | None = None,
    ) -> RAGResponse:
        """
        Ejecuta el pipeline RAG completo para una consulta.

        Args:
            query: Pregunta del usuario.
            filter_type: Filtro opcional por tipo de fuente ("github", "web", "document").

        Returns:
            RAGResponse con respuesta, fuentes y metadatos.
        """
        if not query or not query.strip():
            return RAGResponse(
                answer="La consulta está vacía.",
                query=query,
                model=self.ollama_model,
            )

        # 1. Recuperar chunks relevantes
        chunks = retrieve_chunks(
            query=query,
            indexer=self.indexer,
            embedding_model=self.embedding_model,
            top_k=self.top_k,
            filter_type=filter_type,
        )

        if not chunks:
            logger.warning("No se encontraron chunks relevantes para la consulta.")
            return RAGResponse(
                answer="No encontré información relevante en los documentos indexados para responder esta pregunta.",
                query=query,
                model=self.ollama_model,
                chunks_used=0,
            )

        # 2. Construir contexto y prompt
        context = build_context(chunks)
        prompt = build_prompt(query, context)

        # 3. Generar respuesta con Ollama/Qwen
        answer = generate_with_ollama(
            prompt=prompt,
            ollama_url=self.ollama_url,
            model=self.ollama_model,
        )

        # 4. Construir lista de fuentes para trazabilidad
        sources = [
            {
                "file": c.file,
                "source": c.source,
                "type": c.type,
                "path": c.path,
                "score": round(c.score, 4),
                "chunk_id": c.chunk_id,
            }
            for c in chunks
        ]

        return RAGResponse(
            answer=answer,
            sources=sources,
            query=query,
            model=self.ollama_model,
            chunks_used=len(chunks),
        )

    def health_check(self) -> dict:
        """
        Verifica que todos los componentes del pipeline están disponibles.

        Returns:
            Dict con estado de cada componente.
        """
        status = {
            "qdrant": False,
            "ollama": False,
            "embedding_model": False,
        }

        # Verificar Qdrant
        try:
            info = self.indexer.collection_info()
            status["qdrant"] = "error" not in info
            status["qdrant_info"] = info
        except Exception as e:
            status["qdrant_error"] = str(e)

        # Verificar Ollama
        try:
            response = httpx.get(
                f"{self.ollama_url}/api/tags",
                timeout=10,
            )
            response.raise_for_status()
            models = [m["name"] for m in response.json().get("models", [])]
            status["ollama"] = True
            status["ollama_models"] = models
            status["model_available"] = any(
                self.ollama_model in m for m in models
            )
        except Exception as e:
            status["ollama_error"] = str(e)

        # Verificar modelo de embeddings
        try:
            test_embed = self.embedding_model.embed_single("test")
            status["embedding_model"] = len(test_embed) > 0
            status["embedding_dim"] = len(test_embed)
        except Exception as e:
            status["embedding_error"] = str(e)

        return status
