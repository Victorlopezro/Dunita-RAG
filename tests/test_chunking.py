"""
test_chunking.py — Tests unitarios del módulo de chunking.
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ingest.chunking import chunk_text, Chunk


def test_chunk_empty_text():
    """Texto vacío debe devolver lista vacía."""
    result = chunk_text(
        text="",
        source="test",
        doc_type="github",
        path="test.py",
        file="test.py",
    )
    assert result == []


def test_chunk_short_text():
    """Texto corto debe producir un único chunk."""
    text = "Este es un texto corto de prueba para verificar el chunking básico."
    result = chunk_text(
        text=text,
        source="https://github.com/test/repo",
        doc_type="github",
        path="README.md",
        file="README.md",
        chunk_size=600,
        chunk_overlap=75,
    )
    assert len(result) >= 1
    assert isinstance(result[0], Chunk)
    assert result[0].type == "github"
    assert result[0].file == "README.md"


def test_chunk_metadata():
    """Los metadatos del chunk deben ser correctos."""
    text = "Párrafo de prueba con contenido suficiente para verificar metadatos."
    result = chunk_text(
        text=text,
        source="https://example.com",
        doc_type="web",
        path="/docs",
        file="index.html",
        ingested_at="2024-01-01T00:00:00Z",
    )
    assert len(result) >= 1
    chunk = result[0]
    assert chunk.source == "https://example.com"
    assert chunk.type == "web"
    assert chunk.path == "/docs"
    assert chunk.file == "index.html"
    assert chunk.ingested_at == "2024-01-01T00:00:00Z"
    assert chunk.chunk_id == 0


def test_chunk_to_payload():
    """El método to_payload debe devolver un dict con todas las claves."""
    text = "Texto de prueba para payload."
    result = chunk_text(
        text=text,
        source="test_source",
        doc_type="document",
        path="/data",
        file="doc.pdf",
    )
    assert len(result) >= 1
    payload = result[0].to_payload()
    required_keys = {"text", "source", "type", "path", "file", "chunk_id", "ingested_at"}
    assert required_keys.issubset(set(payload.keys()))


def test_chunk_long_text_produces_multiple_chunks():
    """Texto largo debe producir múltiples chunks."""
    # Generar texto de ~2000 tokens
    paragraph = "Este es un párrafo de prueba con contenido relevante. " * 20
    text = "\n\n".join([paragraph] * 5)

    result = chunk_text(
        text=text,
        source="test",
        doc_type="github",
        path="large_file.py",
        file="large_file.py",
        chunk_size=200,
        chunk_overlap=30,
    )
    assert len(result) > 1
    # Los chunk_ids deben ser consecutivos
    chunk_ids = [c.chunk_id for c in result]
    assert chunk_ids == list(range(len(result)))
