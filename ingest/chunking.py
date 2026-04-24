"""
chunking.py — División de texto en chunks con overlap.

Estrategia: split por párrafos primero, luego agrupa hasta alcanzar
el tamaño objetivo. Usa tiktoken para contar tokens con precisión.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List

import tiktoken
from loguru import logger


# Tokenizador compatible con la mayoría de modelos
_ENCODING = tiktoken.get_encoding("cl100k_base")


@dataclass
class Chunk:
    """Representa un fragmento de texto con sus metadatos."""

    text: str
    source: str
    type: str          # "github" | "web" | "document"
    path: str
    file: str
    chunk_id: int
    ingested_at: str = field(default="")

    def to_payload(self) -> dict:
        """Serializa el chunk como payload para Qdrant."""
        return {
            "text": self.text,
            "source": self.source,
            "type": self.type,
            "path": self.path,
            "file": self.file,
            "chunk_id": self.chunk_id,
            "ingested_at": self.ingested_at,
        }


def _count_tokens(text: str) -> int:
    """Cuenta tokens usando tiktoken (cl100k_base)."""
    return len(_ENCODING.encode(text))


def _split_into_paragraphs(text: str) -> List[str]:
    """Divide el texto en párrafos usando líneas en blanco como separador."""
    paragraphs = re.split(r"\n{2,}", text.strip())
    # Filtra párrafos vacíos o con solo espacios
    return [p.strip() for p in paragraphs if p.strip()]


def chunk_text(
    text: str,
    source: str,
    doc_type: str,
    path: str,
    file: str,
    ingested_at: str = "",
    chunk_size: int = 600,
    chunk_overlap: int = 75,
) -> List[Chunk]:
    """
    Divide `text` en chunks de aproximadamente `chunk_size` tokens
    con solapamiento de `chunk_overlap` tokens entre chunks consecutivos.

    Args:
        text: Texto completo a dividir.
        source: URL o ruta raíz del documento.
        doc_type: Tipo de fuente ("github", "web", "document").
        path: Ruta relativa dentro del repo o URL de la página.
        file: Nombre del archivo o título de la página.
        ingested_at: Timestamp ISO de ingesta.
        chunk_size: Número objetivo de tokens por chunk.
        chunk_overlap: Tokens de solapamiento entre chunks.

    Returns:
        Lista de objetos Chunk.
    """
    if not text or not text.strip():
        logger.warning(f"Texto vacío recibido para {path}/{file}, se omite.")
        return []

    paragraphs = _split_into_paragraphs(text)
    chunks: List[Chunk] = []
    current_tokens: List[str] = []  # tokens del chunk actual (como texto)
    current_text_parts: List[str] = []
    chunk_id = 0

    for para in paragraphs:
        para_tokens = _count_tokens(para)

        # Si el párrafo solo ya supera el chunk_size, lo dividimos por frases
        if para_tokens > chunk_size:
            sentences = re.split(r"(?<=[.!?])\s+", para)
            for sentence in sentences:
                sent_tokens = _count_tokens(sentence)
                current_size = _count_tokens(" ".join(current_text_parts))

                if current_size + sent_tokens > chunk_size and current_text_parts:
                    # Guardar chunk actual
                    chunk_text_str = " ".join(current_text_parts)
                    chunks.append(
                        Chunk(
                            text=chunk_text_str,
                            source=source,
                            type=doc_type,
                            path=path,
                            file=file,
                            chunk_id=chunk_id,
                            ingested_at=ingested_at,
                        )
                    )
                    chunk_id += 1

                    # Overlap: conservar las últimas palabras
                    overlap_text = _get_overlap_text(chunk_text_str, chunk_overlap)
                    current_text_parts = [overlap_text] if overlap_text else []

                current_text_parts.append(sentence)
        else:
            current_size = _count_tokens(" ".join(current_text_parts))
            if current_size + para_tokens > chunk_size and current_text_parts:
                # Guardar chunk actual
                chunk_text_str = " ".join(current_text_parts)
                chunks.append(
                    Chunk(
                        text=chunk_text_str,
                        source=source,
                        type=doc_type,
                        path=path,
                        file=file,
                        chunk_id=chunk_id,
                        ingested_at=ingested_at,
                    )
                )
                chunk_id += 1

                # Overlap
                overlap_text = _get_overlap_text(chunk_text_str, chunk_overlap)
                current_text_parts = [overlap_text] if overlap_text else []

            current_text_parts.append(para)

    # Guardar el último chunk si tiene contenido
    if current_text_parts:
        final_text = " ".join(current_text_parts).strip()
        if final_text:
            chunks.append(
                Chunk(
                    text=final_text,
                    source=source,
                    type=doc_type,
                    path=path,
                    file=file,
                    chunk_id=chunk_id,
                    ingested_at=ingested_at,
                )
            )

    logger.debug(f"Chunking completado: {len(chunks)} chunks para {file}")
    return chunks


def _get_overlap_text(text: str, overlap_tokens: int) -> str:
    """
    Extrae los últimos `overlap_tokens` tokens de `text` como texto.
    Usado para mantener contexto entre chunks consecutivos.
    """
    tokens = _ENCODING.encode(text)
    if len(tokens) <= overlap_tokens:
        return text
    overlap_token_ids = tokens[-overlap_tokens:]
    return _ENCODING.decode(overlap_token_ids)
