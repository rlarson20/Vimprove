"""Tests for API endpoints."""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch


@pytest.fixture
def mock_retriever():
    """Mock retriever for testing."""
    retriever = Mock()
    retriever.search.return_value = [
        {
            "id": "test-id",
            "text": "Test documentation text",
            "metadata": {"source": "test-plugin", "type": "markdown"},
            "distance": 0.5,
        }
    ]
    retriever.collection.count.return_value = 100
    return retriever


@pytest.fixture
def client(mock_retriever):
    """Test client with mocked dependencies."""
    with patch("api.retriever", mock_retriever):
        with patch("api.openrouter_key", "test-key"):
            from api import app

            return TestClient(app)


def test_health_endpoint(client):
    """Test health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["retriever_loaded"] is True


def test_query_endpoint_missing_retriever():
    """Test query endpoint fails without retriever."""
    with patch("api.retriever", None):
        from api import app

        client = TestClient(app)
        response = client.post("/query", json={"query": "test"})
        assert response.status_code == 503
