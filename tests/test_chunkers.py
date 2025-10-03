"""Tests for document chunkers."""

from src.vim_doc_chunker import chunk_vimdoc
from src.readme_chunker import chunk_markdown


def test_vimdoc_chunker_basic():
    """Test basic vimdoc chunking."""
    sample = """
==============================================================================
SECTION HEADING                                              *section-tag*

Some prose here. Tags can appear inline like |:command|.

    vim.opt.number = true

------------------------------------------------------------------------------
ANOTHER HEADING                                              *another-tag*

More content here.
"""

    chunks = chunk_vimdoc(sample, "test-source")

    assert len(chunks) == 2
    assert chunks[0]["type"] == "vimdoc"
    assert chunks[0]["source"] == "test-source"
    assert "section-tag" in chunks[0]["tags"]
    assert "vim.opt.number = true" in chunks[0]["text"]


def test_vimdoc_chunker_empty():
    """Test vimdoc chunker with empty input."""
    chunks = chunk_vimdoc("", "test-source")
    assert len(chunks) == 0


def test_markdown_chunker_basic():
    """Test basic markdown chunking."""
    sample = """# Plugin Name

Description here.

## Installation

Using lazy.nvim:
```lua
{ 'author/plugin' }
Usage
Some usage info.
"""
    chunks = chunk_markdown(sample, "test-source")

    assert len(chunks) >= 2
    assert chunks[0]["type"] == "markdown"
    assert chunks[0]["source"] == "test-source"

    # Check heading hierarchy
    install_chunk = next(c for c in chunks if "Installation" in c.get("headings", []))
    assert "lazy.nvim" in install_chunk["text"]


def test_markdown_chunker_skips_html():
    """Test that markdown chunker skips HTML."""
    sample = """# Title

<div class="badge">
  <img src="badge.png" />
</div>

Some text.
"""
    chunks = chunk_markdown(sample, "test-source")

    # Should have only the text, not HTML
    assert len(chunks) == 1
    assert "Some text" in chunks[0]["text"]
    assert "<div" not in chunks[0]["text"]
