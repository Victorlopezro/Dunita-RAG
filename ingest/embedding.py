"""
embedding.py — Generación de embeddings con SBERT (sentence-transformers).

Expone una clase EmbeddingModel con caché singleton para evitar
recargar el modelo en cada llamada.
"""

from __future__ import annotations

from functools import lru_cache
from typing import List

import numpy as np
from loguru import logger
from sentence_transformers import SentenceTransformer


class EmbeddingModel:
    """
    Wrapper sobre SentenceTransformer con inicialización lazy.
    Mantiene el modelo cargado en memoria durante la vida del proceso.
    """

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model_name = model_name
        self._model: SentenceTransformer | None = None
        logger.info(f"EmbeddingModel inicializado con modelo: {model_name}")

    def _load(self) -> SentenceTransformer:
        """Carga el modelo si aún no está en memoria."""
        if self._model is None:
            logger.info(f"Cargando modelo SBERT: {self.model_name}")
            self._model = SentenceTransformer(self.model_name)
            logger.info("Modelo SBERT cargado correctamente.")
        return self._model

    def embed(self, texts: List[str]) -> List[List[float]]:
        """
        Genera embeddings para una lista de textos.

        Args:
            texts: Lista de strings a vectorizar.

        Returns:
            Lista de vectores (listas de floats).
        """
        if not texts:
            return []

        model = self._load()
        logger.debug(f"Generando embeddings para {len(texts)} textos...")
        embeddings: np.ndarray = model.encode(
            texts,
            batch_size=32,
            show_progress_bar=False,
            normalize_embeddings=True,
        )
        return embeddings.tolist()

    def embed_single(self, text: str) -> List[float]:
        """
        Genera embedding para un único texto.

        Args:
            text: String a vectorizar.

        Returns:
            Vector como lista de floats.
        """
        result = self.embed([text])
        return result[0] if result else []

    @property
    def dimension(self) -> int:
        """Devuelve la dimensión del vector de embedding."""
        model = self._load()
        return model.get_sentence_embedding_dimension()


@lru_cache(maxsize=1)
def get_embedding_model(model_name: str = "all-MiniLM-L6-v2") -> EmbeddingModel:
    """
    Devuelve la instancia singleton del modelo de embeddings.
    Usar esta función en lugar de instanciar EmbeddingModel directamente.
    """
    return EmbeddingModel(model_name)
