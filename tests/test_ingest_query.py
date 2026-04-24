"""
test_ingest_query.py — Tests de los endpoints /ingest y /query.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.main import app

client = TestClient(app)


# ─────────────────────────────────────────────────────────────
# Tests de /ingest
# ─────────────────────────────────────────────────────────────

def test_ingest_github_missing_urls():
    """Debe devolver 422 si no se proporcionan URLs para ingesta GitHub."""
    response = client.post("/ingest", json={"source_type": "github"})
    assert response.status_code == 422


def test_ingest_web_missing_urls():
    """Debe devolver 422 si no se proporcionan URLs para ingesta web."""
    response = client.post("/ingest", json={"source_type": "web"})
    assert response.status_code == 422


def test_ingest_invalid_source_type():
    """Debe devolver 422 para un tipo de fuente inválido."""
    response = client.post(
        "/ingest",
        json={"source_type": "invalid_type", "urls": ["https://example.com"]},
    )
    assert response.status_code == 422


def test_ingest_web_success():
    """Debe procesar correctamente una ingesta web mockeada."""
    with patch("api.services.ingest_service.ingest_web") as mock_ingest:
        mock_ingest.return_value = {
            "documents_processed": 2,
            "chunks_indexed": 15,
            "errors": [],
            "urls_attempted": 2,
        }
        response = client.post(
            "/ingest",
            json={
                "source_type": "web",
                "urls": ["https://example.com", "https://example.com/docs"],
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["documents_processed"] == 2
        assert data["chunks_indexed"] == 15


# ─────────────────────────────────────────────────────────────
# Tests de /query
# ─────────────────────────────────────────────────────────────

def test_query_empty_string():
    """Debe devolver 422 para una consulta vacía."""
    response = client.post("/query", json={"query": ""})
    assert response.status_code == 422


def test_query_too_long():
    """Debe devolver 422 para una consulta demasiado larga."""
    response = client.post("/query", json={"query": "x" * 2001})
    assert response.status_code == 422


def test_query_success():
    """Debe devolver una respuesta válida para una consulta correcta."""
    with patch("api.routes.query.run_query") as mock_query:
        mock_query.return_value = {
            "answer": "El sistema usa Haystack y Qdrant.",
            "sources": [
                {
                    "file": "README.md",
                    "source": "https://github.com/test/repo",
                    "type": "github",
                    "path": "README.md",
                    "score": 0.95,
                    "chunk_id": 0,
                }
            ],
            "query": "¿Qué tecnologías usa el sistema?",
            "model": "qwen2.5:7b",
            "chunks_used": 1,
        }
        response = client.post(
            "/query",
            json={"query": "¿Qué tecnologías usa el sistema?"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "answer" in data
        assert "sources" in data
        assert data["chunks_used"] == 1
        assert len(data["sources"]) == 1
        assert data["sources"][0]["file"] == "README.md"
