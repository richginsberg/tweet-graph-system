#!/bin/bash
# Fetch all bookmarks (full sync)

cd /home/machinelearning/.openclaw/workspace/tweet-graph-system/bookmark-fetcher

source venv/bin/activate
export TWEET_GRAPH_API_URL=http://localhost:8000

# Run full fetch
python -m fetcher.main_playwright
