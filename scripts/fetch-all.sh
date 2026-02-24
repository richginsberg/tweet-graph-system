#!/bin/bash
# Fetch all bookmarks (full sync)
#
# Generic script - works from any installation location

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR/bookmark-fetcher"

if [ -d "venv" ]; then
    source venv/bin/activate
fi
export TWEET_GRAPH_API_URL=http://localhost:8000

# Run full fetch
python -m fetcher.main_playwright --full
