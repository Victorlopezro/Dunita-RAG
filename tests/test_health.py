"""
test_health.py — Tests del endpoint /health.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.main import app

client = TestClient(app)


def test_root():
    """El endpoint raíz debe devolver información del servicio."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "rag-rack API"


def test_health_endpoint_exists():
    """El endpoint /health debe existir y devolver un JSON válido."""
    with patch("api.routes.health.get_system_health") as mock_health:
        mock_health.return_value = {
            "qdrant": True,
            "ollama": True,
            "embedding_model": True,
        }
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] == "ok"


def test_health_degraded_when_component_fails():
    """El endpoint /health debe devolver 503 si algún componente falla."""
    with patch("api.routes.health.get_system_health") as mock_health:
        mock_health.return_value = {
            "qdrant": False,
            "ollama": True,
            "embedding_model": True,
        }
        response = client.get("/health")
        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "degraded"
