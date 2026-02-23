#!/bin/bash
# Direct entry point for tweet graph skill
# This is what OpenClaw should execute

cd ~/.openclaw/workspace/workspace/tweet-graph-system
source bookmark-fetcher/venv/bin/activate

QUERY="${1:-}"
OUTPUT="~/.openclaw/workspace/tweet-graph.png"

echo "[$(date)] Running with query='$QUERY'" >> /tmp/tweet-skill-exec.log

python3 scripts/render_graph.py "$QUERY" "$OUTPUT" 2>> /tmp/tweet-skill-exec.log

echo "[$(date)] Output: $(ls -la $OUTPUT 2>&1)" >> /tmp/tweet-skill-exec.log

echo "$OUTPUT"
