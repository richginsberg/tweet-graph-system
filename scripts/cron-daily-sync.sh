#!/bin/bash
# Daily Incremental Bookmark Sync
# Fetches new bookmarks since last run
#
# Add to crontab:
#   0 6 * * * /path/to/tweet-graph-system/scripts/cron-daily-sync.sh >> /var/log/tweet-graph-sync.log 2>&1
#
# Or use OpenClaw cron:
#   openclaw cron add --schedule "0 6 * * *" --script /path/to/cron-daily-sync.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
STATE_FILE="$PROJECT_DIR/bookmark-fetcher/state.json"
LOG_PREFIX="[daily-sync $(date '+%Y-%m-%d %H:%M:%S')]"

echo "$LOG_PREFIX Starting daily bookmark sync..."

# Check if services are running
if ! curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo "$LOG_PREFIX ERROR: Tweet Graph API not running on port 8000"
    exit 1
fi

# Run the fetcher
cd "$PROJECT_DIR/bookmark-fetcher"

# Activate virtual environment if exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Run fetch and capture output
python -m fetcher.main_playwright 2>&1 | while read -r line; do
    echo "$LOG_PREFIX $line"
done

# Check results
STATS=$(curl -s http://localhost:8000/stats)
TWEET_COUNT=$(echo "$STATS" | python3 -c "import sys, json; print(json.load(sys.stdin).get('tweets', 0))")

echo "$LOG_PREFIX Sync complete. Total tweets in graph: $TWEET_COUNT"
