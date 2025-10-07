#!/bin/bash
# Start Vimprove API server as background service

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

# Load environment
if [ -f .env ]; then
	export $(cat .env | xargs)
fi

# Check requirements
if [ -z "$OPENROUTER_API_KEY" ]; then
	echo "Error: OPENROUTER_API_KEY not set"
	exit 1
fi

# Start server
echo "Starting Vimprove API server..."
uv run api.py --host 0.0.0.0 --port 8000 >vimprove.log 2>&1 &

PID=$!
echo $PID >vimprove.pid

echo "✓ Server started (PID: $PID)"
echo "  Logs: tail -f vimprove.log"
echo "  Stop: kill $(cat vimprove.pid)"
