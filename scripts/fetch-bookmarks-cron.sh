#!/bin/bash
# Daily bookmark fetch cron script

cd /home/machinelearning/.openclaw/workspace/tweet-graph-system/bookmark-fetcher

# Activate venv
source venv/bin/activate

# Export API URL
export TWEET_GRAPH_API_URL=http://localhost:8000

# Run fetcher (no limit = fetch all)
python -m fetcher.main_playwright

# Log result
echo "$(date): Bookmark fetch completed" >> /var/log/tweet-graph-bookmarks.log
