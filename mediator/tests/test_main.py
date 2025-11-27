"""Basic tests for main application."""

import os
import pytest
from fastapi.testclient import TestClient

# Set test environment variables
os.environ["MEDIATOR_PAT"] = "test-token"
os.environ["SQLITE_PATH"] = "/tmp/test_mediator.sqlite"
os.environ["CHROMA_URL"] = "http://localhost:8000"

from app.main import app

client = TestClient(app)


def test_root():
    """Test root endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "Synm Mediator"
    assert data["version"] == "0.1.0"
    assert data["status"] == "operational"


def test_health():
    """Test health endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "timestamp" in data


def test_session_creation_no_auth():
    """Test session creation without authentication."""
    response = client.post("/v1/session")
    assert response.status_code == 422  # Missing authorization header


def test_session_creation_invalid_auth():
    """Test session creation with invalid authentication."""
    headers = {"Authorization": "Bearer invalid-token"}
    response = client.post("/v1/session", headers=headers)
    assert response.status_code == 401


def test_session_creation_valid_auth():
    """Test session creation with valid authentication."""
    headers = {"Authorization": "Bearer test-token"}
    response = client.post("/v1/session", headers=headers)
    assert response.status_code == 200
    
    data = response.json()
    assert "session_id" in data
    assert data["profile"] == "default"
    assert "expires_at" in data


def test_context_request_no_session():
    """Test context request for non-existent session."""
    headers = {"Authorization": "Bearer test-token"}
    payload = {
        "session_id": "non-existent",
        "profile": "work",
        "scopes": ["bio.basic"],
        "prompt": "Tell me about yourself"
    }
    
    response = client.post("/v1/context", json=payload, headers=headers)
    assert response.status_code == 404