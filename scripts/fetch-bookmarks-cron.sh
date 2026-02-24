#!/bin/bash
# Daily bookmark fetch cron script
#
# Generic script - works from any installation location
# Add to crontab:
#   0 6 * * * /path/to/tweet-graph-system/scripts/fetch-bookmarks-cron.sh >> /var/log/tweet-graph.log 2>&1

# Get script directory (works regardless of where script is called from)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR/bookmark-fetcher"

# Activate venv if exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Export API URL
export TWEET_GRAPH_API_URL=http://localhost:8000

# Run fetcher (no limit = fetch all)
python -m fetcher.main_playwright

# Log result
echo "$(date): Bookmark fetch completed" >> /var/log/tweet-graph-bookmarks.log
