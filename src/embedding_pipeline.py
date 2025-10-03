#!/usr/bin/env python3
"""
Vimprove embedding pipeline.
Embeds documentation chunks and stores in vector DB.

Usage:
    python embedding_pipeline.py [--force]
"""

import argparse
import json
from pathlib import Path
from typing import Any
import hashlib

from sentence_transformers import SentenceTransformer
import chromadb
from chromadb.config import Settings
from tqdm import tqdm


class VimproveEmbedder:
    def __init__(
        self, cache_dir: Path, model_name: str = "all-MiniLM-L6-v2", force: bool = False
    ):
        self.cache_dir = cache_dir
        self.chunks_dir = cache_dir / "chunks"
        self.vector_db_dir = cache_dir / "vector_db"
        self.force = force

        print("Loading embedding model...")
        self.model = SentenceTransformer(model_name)
        print(f"✓ Loaded {model_name}")

        print("Initializing vector database...")
        self.client = chromadb.PersistentClient(
            path=str(self.vector_db_dir),
            settings=Settings(anonymized_telemetry=False, allow_reset=True),
        )

        # Single collection for all docs
        if self.force:
            try:
                self.client.delete_collection("vimprove_docs")
                print("  Deleted existing collection (force mode)")
            except ValueError:
                print("Error: Collection does not exist")
                pass

        self.collection = self.client.get_or_create_collection(
            name="vimprove_docs",
            metadata={"description": "Neovim and plugin documentation"},
        )
        print(f"✓ Collection ready ({self.collection.count()} existing chunks)")

    def run(self):
        """Execute embedding pipeline."""
        print("\n" + "=" * 60)
        print("Vimprove Embedding Pipeline")
        print("=" * 60)

        # Collect all chunk files
        print("\n[1/3] Scanning chunk files...")
        chunk_files = self._collect_chunk_files()
        print(f"  Found {len(chunk_files)} chunk files")

        # Load and prepare chunks
        print("\n[2/3] Loading chunks...")
        chunks_to_embed = self._load_chunks(chunk_files)
        print(f"  Loaded {len(chunks_to_embed)} chunks")

        if not chunks_to_embed:
            print("\n✓ All chunks already embedded")
            return

        # Embed and store
        print(f"\n[3/3] Embedding {len(chunks_to_embed)} chunks...")
        self._embed_and_store(chunks_to_embed)

        print("\n" + "=" * 60)
        print("✓ Embedding complete")
        print(f"  Total chunks in DB: {self.collection.count()}")
        print(f"  Vector DB stored in: {self.vector_db_dir}")
        print("=" * 60)

    def _collect_chunk_files(self) -> list[Path]:
        """Find all chunk JSON files."""
        chunk_files = []

        # Neovim core
        core_dir = self.chunks_dir / "neovim-core"
        if core_dir.exists():
            chunk_files.extend(core_dir.glob("*.json"))

        # Plugins
        plugins_dir = self.chunks_dir / "plugins"
        if plugins_dir.exists():
            chunk_files.extend(plugins_dir.glob("*.json"))

        return sorted(chunk_files)

    def _load_chunks(self, chunk_files: list[Path]) -> list[dict[str, Any]]:
        """Load chunks from JSON files, skipping already-embedded ones."""
        chunks_to_embed = []

        for chunk_file in tqdm(chunk_files, desc="Loading"):
            try:
                with open(chunk_file, encoding="utf-8") as f:
                    data = json.load(f)

                # Handle metadata wrapper
                if isinstance(data, dict) and "chunks" in data:
                    chunks = data["chunks"]
                else:
                    chunks = data

                for chunk in chunks:
                    chunk_id = self._generate_chunk_id(chunk)

                    # Skip if already in DB (unless force mode)
                    if not self.force:
                        existing = self.collection.get(ids=[chunk_id])
                        if existing["ids"]:
                            continue

                    chunks_to_embed.append(chunk)

            except Exception as e:
                print(f"  ✗ Error loading {chunk_file.name}: {e}")

        return chunks_to_embed

    def _generate_chunk_id(self, chunk: dict[str, Any], counter: int = 0) -> str:
        """Generate deterministic ID for chunk based on content and metadata."""
        parts = [chunk["source"], chunk["type"], chunk["text"]]

        # Add type-specific metadata for uniqueness
        if chunk["type"] == "vimdoc":
            if chunk.get("heading"):
                parts.append(chunk["heading"])
            if chunk.get("tags"):
                parts.append(",".join(chunk["tags"]))
        elif chunk["type"] == "markdown":
            if chunk.get("headings"):
                parts.append(" > ".join(chunk["headings"]))

        # Add counter if > 0 (for handling true duplicates within batch)
        if counter > 0:
            parts.append(str(counter))

        content = "|||".join(parts)
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    def _embed_and_store(self, chunks: list[dict[str, any]]):
        """Embed chunks and store in Chroma."""
        batch_size = 32

        for i in tqdm(range(0, len(chunks), batch_size), desc="Embedding"):
            batch = chunks[i : i + batch_size]

            # Extract texts for embedding
            texts = [chunk["text"] for chunk in batch]

            # Generate embeddings
            embeddings = self.model.encode(
                texts, show_progress_bar=False, convert_to_numpy=True
            ).tolist()

            # Prepare IDs with duplicate handling
            ids = []
            seen_ids = set()
            counter_map = {}

            for chunk in batch:
                base_id = self._generate_chunk_id(chunk, 0)

                # Handle duplicates within batch
                if base_id in seen_ids:
                    counter_map[base_id] = counter_map.get(base_id, 0) + 1
                    chunk_id = self._generate_chunk_id(chunk, counter_map[base_id])
                else:
                    chunk_id = base_id

                ids.append(chunk_id)
                seen_ids.add(chunk_id)

            metadatas = [self._prepare_metadata(chunk) for chunk in batch]

            # Store in Chroma
            self.collection.add(
                ids=ids, embeddings=embeddings, documents=texts, metadatas=metadatas
            )

    def _prepare_metadata(self, chunk: dict[str, Any]) -> dict[str, Any]:
        """Prepare chunk metadata for Chroma storage."""
        metadata = {"source": chunk["source"], "type": chunk["type"]}

        # Add type-specific metadata
        if chunk["type"] == "vimdoc":
            if chunk.get("heading"):
                metadata["heading"] = chunk["heading"]
            if chunk.get("tags"):
                # Chroma doesn't support list metadata, join as string
                metadata["tags"] = ",".join(chunk["tags"])

        elif chunk["type"] == "markdown":
            if chunk.get("headings"):
                # Store as hierarchical string
                metadata["headings"] = " > ".join(chunk["headings"])

        return metadata


def main():
    parser = argparse.ArgumentParser(
        description="Embed documentation chunks into vector database"
    )
    parser.add_argument(
        "--cache-dir",
        type=Path,
        default=Path("./vimprove-cache").resolve(),
        help="Cache directory (default: ./vimprove-cache)",
    )
    parser.add_argument(
        "--model",
        type=str,
        default="all-MiniLM-L6-v2",
        help="SentenceTransformer model name (default: all-MiniLM-L6-v2)",
    )
    parser.add_argument(
        "--force", action="store_true", help="Force re-embed all chunks"
    )

    args = parser.parse_args()

    embedder = VimproveEmbedder(
        cache_dir=args.cache_dir, model_name=args.model, force=args.force
    )

    try:
        embedder.run()
        return 0
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        return 130
    except Exception as e:
        print(f"\n✗ Fatal error: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())
