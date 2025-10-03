from datetime import datetime
import json
from pathlib import Path


def save_chunks(chunks: list[dict[str, any]], source: str, output_path: Path):
    """Save chunks with metadata wrapper."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    data = {
        "source": source,
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "chunk_count": len(chunks),
        "chunks": chunks,
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def load_chunks(chunk_file: Path) -> list[dict[str, any]]:
    """Load chunks from file, handling metadata wrapper."""
    with open(chunk_file, encoding="utf-8") as f:
        data = json.load(f)

    # Handle both formats (with and without metadata)
    if isinstance(data, list):
        return data
    return data.get("chunks", [])
