#!/bin/bash
# Debug wrapper for tweet graph renderer
# Logs all output for troubleshooting

LOG_FILE="/tmp/tweet-graph-debug.log"
OUTPUT_FILE="~/.openclaw/workspace/tweet-graph.png"

echo "=== $(date) ===" >> "$LOG_FILE"
echo "Args: $@" >> "$LOG_FILE"
echo "Query: '$1'" >> "$LOG_FILE"

cd ~/.openclaw/workspace/workspace/tweet-graph-system
source bookmark-fetcher/venv/bin/activate

# Test API connectivity
echo "Testing API..." >> "$LOG_FILE"
curl -s http://localhost:8000/stats >> "$LOG_FILE" 2>&1
echo "" >> "$LOG_FILE"

# Run renderer with full output
echo "Running renderer..." >> "$LOG_FILE"
python3 scripts/render_graph.py "$1" "/tmp/tweet-graph-tmp.png" >> "$LOG_FILE" 2>&1

# Copy to output location
cp /tmp/tweet-graph-tmp.png "$OUTPUT_FILE" 2>> "$LOG_FILE"

echo "Output: $(ls -la $OUTPUT_FILE)" >> "$LOG_FILE"
echo "" >> "$LOG_FILE"

# Return path for skill to use
echo "$OUTPUT_FILE"
