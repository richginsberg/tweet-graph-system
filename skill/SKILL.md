---
name: tweet-graph
description: "Import and analyze X/Twitter bookmarks as a Neo4j knowledge graph. Use when: (1) user wants to sync/import bookmarks, (2) semantic search over tweets, (3) view tweet graph visualization, (4) analyze themes/entities from bookmarks. Requires Docker and X/Twitter cookies."
metadata:
  {
    "openclaw":
      {
        "emoji": "🐦",
        "requires": { "bins": ["docker", "python3"] },
        "install":
          [
            {
              "id": "docker",
              "kind": "brew",
              "formula": "docker",
              "bins": ["docker"],
              "label": "Install Docker (brew)",
            },
          ],
      },
  }
---

# Tweet Graph Skill

Import X/Twitter bookmarks into a Neo4j knowledge graph with automatic theme extraction, semantic search, and visualization.

## When to Use

✅ **USE this skill when:**

- "Sync my Twitter bookmarks"
- "Search my tweets about AI"
- "Show tweet graph"
- "What themes are in my bookmarks?"
- "Import bookmarks"
- "Show truncated tweets"

## When NOT to Use

❌ **DON'T use this skill when:**

- Posting tweets to X/Twitter → use X API directly
- Real-time Twitter monitoring → use Twitter streaming API
- Public tweet analysis → use Twitter API v2

## Project Location

```
$HOME/.openclaw/workspace/workspace/tweet-graph-system
```

## Setup

### First Time

```bash
# 1. Navigate to project
cd $HOME/.openclaw/workspace/workspace/tweet-graph-system

# 2. Start services
docker-compose up -d

# 3. Wait for services
sleep 10

# 4. Configure environment
cp .env.example .env
# Edit .env with your API keys

# 5. Export X/Twitter cookies
# - Log into x.com in your browser
# - Use browser dev tools to export cookies
# - Save to bookmark-fetcher/cookies.json

# 6. Run initial import
cd bookmark-fetcher
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python -m fetcher.main_playwright --full
```

## Commands

### Sync Bookmarks

```bash
# Full import (all bookmarks)
cd $HOME/.openclaw/workspace/workspace/tweet-graph-system/bookmark-fetcher
source venv/bin/activate
python -m fetcher.main_playwright --full

# Incremental (only new)
python -m fetcher.main_playwright
```

### Query Stats

```bash
curl -s http://localhost:8000/stats | jq .
```

### Search Tweets

```bash
curl -X POST http://localhost:8000/search \
  -H "Content-Type: application/json" \
  -d '{"query": "artificial intelligence", "limit": 10}' | jq .
```

### Truncated Tweets

```bash
curl -s http://localhost:8000/tweets/truncated | jq '.count'
```

### Themes

```bash
curl -s http://localhost:8000/themes | jq .
```

## Portal Access

| Page | URL |
|------|-----|
| Dashboard | http://localhost:3000 |
| Graph | http://localhost:3000/graph |
| Search | http://localhost:3000/search |
| Tweets | http://localhost:3000/tweets |
| Themes | http://localhost:3000/themes |

## API Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /stats` | Graph statistics |
| `GET /themes` | Extracted themes |
| `GET /entities` | Extracted entities |
| `GET /tweets/truncated` | Tweets needing enrichment |
| `POST /search` | Semantic search |
| `POST /bookmarks/sync` | Bulk import |

## Automatic Processing

When bookmarks are synced, the system automatically:

1. **Extracts Themes** - AI, LLM, crypto, dev, business, etc.
2. **Extracts Entities** - Proper nouns (people, companies)
3. **Extracts Hashtags** - From tweet text
4. **Extracts Mentions** - @usernames
5. **Generates Embeddings** - For semantic search
6. **Detects Truncation** - Marks incomplete tweets

## Services

| Service | Port | Description |
|---------|------|-------------|
| API | 8000 | FastAPI backend |
| Portal | 3000 | Next.js frontend |
| Neo4j | 7474, 7687 | Graph database |

## Troubleshooting

```bash
# Check services
docker-compose ps

# View logs
docker-compose logs api
docker-compose logs neo4j

# Restart
docker-compose restart

# Full reset
docker-compose down -v
docker-compose up -d
```

## Requirements

- Docker & Docker Compose
- Python 3.10+
- X/Twitter cookies (for bookmark access)
- Optional: X API Bearer Token (for truncation enrichment)
- Embedding API key (OpenAI, Chutes.ai, etc.)
