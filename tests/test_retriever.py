"""Tests for VimproveRetriever."""

import pytest
from pathlib import Path
from src.retriever import VimproveRetriever


@pytest.fixture
def retriever():
    """Real retriever against test DB."""
    cache = Path("./vimprove-cache")
    if not cache.exists():
        pytest.skip("Vector DB not built")
    return VimproveRetriever(cache)


def test_retriever_loads(retriever):
    assert retriever.collection.count() > 0


def test_search_returns_results(retriever):
    results = retriever.search("telescope commands", n_results=5)
    assert len(results) > 0
    assert all("text" in r for r in results)
    assert all("metadata" in r for r in results)


def test_search_source_filter(retriever):
    results = retriever.search("keymaps", n_results=10, source_filter="neovim-core")
    assert all(r["metadata"]["source"] == "neovim-core" for r in results)


def test_search_type_filter(retriever):
    results = retriever.search("install", n_results=10, type_filter="markdown")
    assert all(r["metadata"]["type"] == "markdown" for r in results)


def test_metadata_preserved(retriever):
    """Ensure vimdoc tags/headings survive embedding roundtrip."""
    results = retriever.search("grepprg", n_results=3)
    core_results = [r for r in results if r["metadata"]["source"] == "neovim-core"]
    assert len(core_results) > 0
    # At least one should have heading or tags
    assert any(
        "heading" in r["metadata"] or "tags" in r["metadata"] for r in core_results
    )
