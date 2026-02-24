# Tweet Graph Skill

Import and analyze your X/Twitter bookmarks as a knowledge graph with Neo4j.

## What it does

- Fetches your X/Twitter bookmarks via browser automation
- Stores tweets in Neo4j graph database
- Extracts themes, entities, hashtags automatically
- Generates embeddings for semantic search
- Provides web portal for visualization and search

## Commands

| Command | Description |
|---------|-------------|
| `/tweet-sync` | Fetch new bookmarks (incremental) |
| `/tweet-full` | Full bookmark import |
| `/tweet-search <query>` | Semantic search tweets |
| `/tweet-stats` | Show graph statistics |
| `/tweet-graph` | Generate graph visualization |
| `/tweet-truncated` | Show tweets needing enrichment |

## Setup

### First Time

```bash
# 1. Start services
cd $HOME/.openclaw/workspace/workspace/tweet-graph-system
docker-compose up -d

# 2. Wait for services
sleep 10

# 3. Export X/Twitter cookies
# - Log into x.com in your browser
# - Use browser dev tools to export cookies
# - Save to bookmark-fetcher/cookies.json

# 4. Run initial import
cd bookmark-fetcher
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python -m fetcher.main_playwright --full
```

### Daily Sync

```bash
# Incremental sync (only new bookmarks)
python -m fetcher.main_playwright
```

## Requirements

- Docker & Docker Compose
- Python 3.10+
- X/Twitter cookies (for bookmark access)
- Optional: X API Bearer Token (for truncation enrichment)

## Portal Access

- Dashboard: http://localhost:3000
- Graph: http://localhost:3000/graph
- Search: http://localhost:3000/search
- Tweets: http://localhost:3000/tweets
- Themes: http://localhost:3000/themes

## API Endpoints

- `GET /stats` - Graph statistics
- `GET /tweets/truncated` - Tweets needing enrichment
- `POST /search` - Semantic search
- `GET /themes` - Extracted themes
- `GET /entities` - Extracted entities

## Notes

- Theme extraction is automatic (keyword-based)
- Entity extraction uses proper noun detection
- Embeddings generated on store (configurable provider)
- Truncated tweets can be enriched via X API v2 (monthly)
