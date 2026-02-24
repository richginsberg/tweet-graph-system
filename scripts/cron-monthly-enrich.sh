#!/bin/bash
# Monthly Truncation Enrichment
# Uses X API v2 to fetch full text for truncated tweets
# Run monthly when API credits reset
#
# Add to crontab:
#   0 3 1 * * /path/to/tweet-graph-system/scripts/cron-monthly-enrich.sh >> /var/log/tweet-graph-enrich.log 2>&1
#
# Or use OpenClaw cron:
#   openclaw cron add --schedule "0 3 1 * *" --script /path/to/cron-monthly-enrich.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
LOG_PREFIX="[monthly-enrich $(date '+%Y-%m-%d %H:%M:%S')]"

echo "$LOG_PREFIX Starting monthly truncation enrichment..."

# Check if services are running
if ! curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo "$LOG_PREFIX ERROR: Tweet Graph API not running on port 8000"
    exit 1
fi

# Check for Twitter API token
if [ -z "$TWITTER_BEARER_TOKEN" ]; then
    # Try to load from .env
    if [ -f "$PROJECT_DIR/.env" ]; then
        export $(grep -v '^#' "$PROJECT_DIR/.env" | grep TWITTER_BEARER_TOKEN | xargs)
    fi
fi

if [ -z "$TWITTER_BEARER_TOKEN" ]; then
    echo "$LOG_PREFIX WARNING: No TWITTER_BEARER_TOKEN set. Skipping enrichment."
    echo "$LOG_PREFIX Set TWITTER_BEARER_TOKEN in environment or .env file."
    exit 0
fi

# Get truncated tweets count
TRUNCATED=$(curl -s http://localhost:8000/tweets/truncated)
TRUNCATED_COUNT=$(echo "$TRUNCATED" | python3 -c "import sys, json; print(json.load(sys.stdin).get('count', 0))")

echo "$LOG_PREFIX Found $TRUNCATED_COUNT truncated tweets to enrich"

if [ "$TRUNCATED_COUNT" -eq 0 ]; then
    echo "$LOG_PREFIX No truncated tweets found. Nothing to do."
    exit 0
fi

# Run enrichment script
cd "$PROJECT_DIR/scripts"

# Activate virtual environment if exists
if [ -d "$PROJECT_DIR/bookmark-fetcher/venv" ]; then
    source "$PROJECT_DIR/bookmark-fetcher/venv/bin/activate"
fi

# Create enrichment runner
python3 << 'PYTHON_SCRIPT'
import asyncio
import httpx
import json
import os
import sys

TWITTER_BEARER_TOKEN = os.environ.get("TWITTER_BEARER_TOKEN")
API_URL = "http://localhost:8000"

async def enrich_truncated():
    """Fetch full text for truncated tweets using X API v2"""
    
    # Get truncated tweets
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{API_URL}/tweets/truncated")
        data = resp.json()
        
    tweets = data.get("tweets", [])
    if not tweets:
        print("No truncated tweets to enrich")
        return {"enriched": 0}
    
    print(f"Enriching {len(tweets)} truncated tweets...")
    
    enriched = 0
    failed = 0
    
    # Process in batches of 100 (X API limit)
    batch_size = 100
    for i in range(0, len(tweets), batch_size):
        batch = tweets[i:i+batch_size]
        tweet_ids = [t["id"] for t in batch]
        
        # Fetch from X API v2
        url = "https://api.twitter.com/2/tweets"
        params = {
            "ids": ",".join(tweet_ids),
            "tweet.fields": "created_at,author_id,entities",
            "expansions": "author_id",
            "user.fields": "username"
        }
        headers = {"Authorization": f"Bearer {TWITTER_BEARER_TOKEN}"}
        
        async with httpx.AsyncClient() as client:
            try:
                resp = await client.get(url, params=params, headers=headers, timeout=30.0)
                
                if resp.status_code == 429:
                    print("Rate limited. Stopping enrichment.")
                    break
                
                if resp.status_code != 200:
                    print(f"API error: {resp.status_code}")
                    failed += len(batch)
                    continue
                
                api_data = resp.json()
                
                # Build author lookup
                authors = {}
                if "includes" in api_data and "users" in api_data["includes"]:
                    for user in api_data["includes"]["users"]:
                        authors[user["id"]] = user.get("username", "")
                
                # Update each tweet
                for tweet in api_data.get("data", []):
                    tweet_id = tweet["id"]
                    full_text = tweet.get("text", "")
                    author_id = tweet.get("author_id")
                    entities = tweet.get("entities", {})
                    
                    hashtags = [h["tag"] for h in entities.get("hashtags", [])]
                    mentions = [m["username"] for m in entities.get("mentions", [])]
                    author = authors.get(author_id, "")
                    
                    # Update via API
                    update_data = {
                        "text": full_text,
                        "hashtags": hashtags,
                        "mentions": mentions,
                        "author_username": author,
                        "truncated": False
                    }
                    
                    async with httpx.AsyncClient() as update_client:
                        # Use sync endpoint which handles updates
                        await update_client.post(
                            f"{API_URL}/bookmarks/sync",
                            json={"bookmarks": [{"id": tweet_id, **update_data}]},
                            timeout=30.0
                        )
                    
                    enriched += 1
                    print(f"Enriched: {tweet_id}")
                
            except Exception as e:
                print(f"Error: {e}")
                failed += len(batch)
    
    return {"enriched": enriched, "failed": failed}

if __name__ == "__main__":
    result = asyncio.run(enrich_truncated())
    print(f"\nEnrichment complete: {result}")
PYTHON_SCRIPT

# Final stats
STATS=$(curl -s http://localhost:8000/stats)
TRUNCATED_AFTER=$(curl -s http://localhost:8000/tweets/truncated | python3 -c "import sys, json; print(json.load(sys.stdin).get('count', 0))")

echo "$LOG_PREFIX Enrichment complete. Remaining truncated: $TRUNCATED_AFTER"
