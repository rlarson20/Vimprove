#!/bin/bash
# Update documentation (for cron)

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

# Load environment
if [ -f .env ]; then
	export $(cat .env | xargs)
fi

echo "Updating Vimprove documentation..."

# Ingest new/changed docs
uv run ingestion_pipeline.py

# Embed new chunks
uv run src/embedding_pipeline.py

echo "✓ Documentation updated"
