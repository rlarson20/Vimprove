"""
Query interface for retrieving relevant documentation chunks.
"""

from pathlib import Path
from typing import Any
from sentence_transformers import SentenceTransformer
import chromadb
from chromadb.config import Settings


class VimproveRetriever:
    def __init__(self, cache_dir: Path, model_name: str = "all-MiniLM-L6-v2"):
        self.cache_dir = cache_dir
        self.vector_db_dir = cache_dir / "vector_db"

        # Load embedding model
        self.model = SentenceTransformer(model_name)

        # Connect to Chroma
        self.client = chromadb.PersistentClient(
            path=str(self.vector_db_dir), settings=Settings(anonymized_telemetry=False)
        )

        self.collection = self.client.get_collection("vimprove_docs")

    def search(
        self,
        query: str,
        n_results: int = 10,
        source_filter: str | None = None,
        type_filter: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Search for relevant documentation chunks.

        Args:
            query: Natural language query
            n_results: Number of results to return
            source_filter: Filter by source (e.g., "neovim-core", "telescope.nvim")
            type_filter: Filter by type ("vimdoc" or "markdown")

        Returns:
            List of results with text, metadata, and relevance scores
        """
        # Embed query
        query_embedding = self.model.encode(query).tolist()

        # Build metadata filter
        where = {}
        if source_filter:
            where["source"] = source_filter
        if type_filter:
            where["type"] = type_filter

        # Query Chroma
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            where=where if where else None,
            include=["metadatas", "documents", "distances"],
        )

        # Format results
        formatted = []
        for i in range(len(results["ids"][0])):
            formatted.append(
                {
                    "id": results["ids"][0][i],
                    "text": results["documents"][0][i],
                    "metadata": results["metadatas"][0][i],
                    "distance": results["distances"][0][i]
                    if "distances" in results
                    else None,
                }
            )

        return formatted


# Test interface
def test_retrieval():
    """Quick test of retrieval."""
    retriever = VimproveRetriever(Path("./vimprove-cache"))

    test_queries = [
        "How do I set up LSP keymaps?",
        "What are the telescope commands?",
        "How to configure lazy loading for plugins?",
        "vim.opt.number documentation",
    ]

    for query in test_queries:
        print(f"\nQuery: {query}")
        print("-" * 60)
        results = retriever.search(query, n_results=3)

        for i, result in enumerate(results, 1):
            print(
                f"\n[{i}] {result['metadata']['source']} (distance: {result['distance']:.3f})"
            )
            print(f"    {result['text'][:150]}...")


if __name__ == "__main__":
    test_retrieval()
