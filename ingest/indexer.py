"""
indexer.py — Indexación de chunks en Qdrant.

Responsabilidades:
- Crear la colección si no existe.
- Hacer upsert de chunks con sus vectores y metadatos.
- Proporcionar utilidades de inspección básica.
"""

from __future__ import annotations

import uuid
from typing import List

from loguru import logger
from qdrant_client import QdrantClient
from qdrant_client.http import models as qdrant_models

from ingest.chunking import Chunk
from ingest.embedding import EmbeddingModel


class QdrantIndexer:
    """
    Gestiona la conexión con Qdrant y las operaciones de indexación.
    """

    def __init__(
        self,
        host: str = "localhost",
        port: int = 6333,
        collection: str = "rag_rack",
        embedding_dim: int = 384,
    ):
        self.collection = collection
        self.embedding_dim = embedding_dim
        self.client = QdrantClient(host=host, port=port, timeout=30)
        logger.info(f"QdrantIndexer conectado a {host}:{port}, colección: {collection}")

    def ensure_collection(self) -> None:
        """
        Crea la colección en Qdrant si no existe.
        Si ya existe, no hace nada (idempotente).
        """
        existing = [c.name for c in self.client.get_collections().collections]
        if self.collection in existing:
            logger.info(f"Colección '{self.collection}' ya existe.")
            return

        logger.info(f"Creando colección '{self.collection}' con dim={self.embedding_dim}...")
        self.client.create_collection(
            collection_name=self.collection,
            vectors_config=qdrant_models.VectorParams(
                size=self.embedding_dim,
                distance=qdrant_models.Distance.COSINE,
            ),
        )
        logger.info(f"Colección '{self.collection}' creada correctamente.")

    def index_chunks(
        self,
        chunks: List[Chunk],
        embedding_model: EmbeddingModel,
        batch_size: int = 64,
    ) -> int:
        """
        Genera embeddings para los chunks y los sube a Qdrant en batches.

        Args:
            chunks: Lista de Chunk a indexar.
            embedding_model: Modelo SBERT para generar vectores.
            batch_size: Número de chunks por batch de upsert.

        Returns:
            Número de chunks indexados correctamente.
        """
        if not chunks:
            logger.warning("No hay chunks para indexar.")
            return 0

        self.ensure_collection()
        total_indexed = 0

        for i in range(0, len(chunks), batch_size):
            batch = chunks[i : i + batch_size]
            texts = [c.text for c in batch]

            # Generar embeddings
            vectors = embedding_model.embed(texts)

            # Construir puntos Qdrant
            points = []
            for chunk, vector in zip(batch, vectors):
                point_id = str(uuid.uuid4())
                points.append(
                    qdrant_models.PointStruct(
                        id=point_id,
                        vector=vector,
                        payload=chunk.to_payload(),
                    )
                )

            # Upsert en Qdrant
            self.client.upsert(
                collection_name=self.collection,
                points=points,
                wait=True,
            )
            total_indexed += len(batch)
            logger.debug(
                f"Batch {i // batch_size + 1}: {len(batch)} chunks indexados "
                f"(total: {total_indexed})"
            )

        logger.info(f"Indexación completada: {total_indexed} chunks en '{self.collection}'.")
        return total_indexed

    def collection_info(self) -> dict:
        """Devuelve información básica sobre la colección."""
        try:
            info = self.client.get_collection(self.collection)
            return {
                "name": self.collection,
                "vectors_count": info.vectors_count,
                "points_count": info.points_count,
                "status": str(info.status),
            }
        except Exception as e:
            logger.error(f"Error al obtener info de colección: {e}")
            return {"error": str(e)}

    def search(
        self,
        query_vector: List[float],
        top_k: int = 5,
        filter_type: str | None = None,
    ) -> List[dict]:
        """
        Búsqueda vectorial en Qdrant.

        Args:
            query_vector: Vector de la consulta.
            top_k: Número de resultados a devolver.
            filter_type: Si se especifica, filtra por tipo de fuente.

        Returns:
            Lista de dicts con texto, score y metadatos.
        """
        query_filter = None
        if filter_type:
            query_filter = qdrant_models.Filter(
                must=[
                    qdrant_models.FieldCondition(
                        key="type",
                        match=qdrant_models.MatchValue(value=filter_type),
                    )
                ]
            )

        results = self.client.search(
            collection_name=self.collection,
            query_vector=query_vector,
            limit=top_k,
            query_filter=query_filter,
            with_payload=True,
        )

        return [
            {
                "text": hit.payload.get("text", ""),
                "score": hit.score,
                "source": hit.payload.get("source", ""),
                "type": hit.payload.get("type", ""),
                "path": hit.payload.get("path", ""),
                "file": hit.payload.get("file", ""),
                "chunk_id": hit.payload.get("chunk_id", 0),
            }
            for hit in results
        ]
