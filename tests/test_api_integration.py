"""End-to-end API tests with real retriever."""

import pytest
from fastapi.testclient import TestClient
from pathlib import Path

pytestmark = pytest.mark.skipif(
    not Path("./vimprove-cache/vector_db").exists(), reason="Requires built vector DB"
)


@pytest.fixture
def client():
    """Client with real retriever, mocked OpenRouter."""
    import api
    from unittest.mock import AsyncMock, patch

    # Mock OpenRouter but use real retriever
    with patch("api.call_openrouter", new_callable=AsyncMock) as mock_call:
        mock_call.return_value = "Test response"
        with TestClient(api.app) as c:
            yield c


def test_query_returns_diverse_sources(client):
    """Check if results span multiple plugins."""
    response = client.post(
        "/query", json={"query": "telescope keymaps", "n_results": 10}
    )
    assert response.status_code == 200
    sources = {s["source"] for s in response.json()["sources"]}
    # Should have both neovim-core AND telescope
    assert len(sources) > 1


def test_source_metadata_complete(client):
    """Verify returned sources have identifying info."""
    response = client.post("/query", json={"query": "grepprg option", "n_results": 5})
    sources = response.json()["sources"]
    core_sources = [s for s in sources if "neovim-core" in s["source"]]
    # At least one core result should have heading or tags
    assert any("heading" in str(s) or "tags" in str(s) for s in core_sources)
