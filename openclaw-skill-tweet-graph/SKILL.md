# Tweet Graph Skill

Store and retrieve tweets in a Neo4j graph database with automatic entity extraction, theme detection, and web portal visualization.

## Purpose

This skill enables storing tweets (from URLs, browser fetch, or manual entry) in a graph database with:
- **Entity extraction**: hashtags, mentions, URLs
- **Theme detection**: AI, crypto, dev, business, infrastructure, etc.
- **Proper noun detection**: OpenAI, Anthropic, Elon Musk, etc.
- **Semantic search**: Vector similarity with embeddings
- **Graph traversal**: Find related tweets

## Quick Commands (Telegram/Chat)

Short commands for quick access:

| Command | Description |
|---------|-------------|
| `/tweets` | Show latest tweets |
| `/search <query>` | Search tweets semantically |
| `/themes` | Show all themes |
| `/stats` | Database statistics |
| `/sync` | Sync X bookmarks |
| `/graph` | Show graph visualization URL |

## Setup

### Environment Variables

```bash
# Required
export TWEET_GRAPH_API_URL=http://localhost:8000

# Optional - for X API v2 enrichment
export TWITTER_BEARER_TOKEN=your_token

# Optional - for embeddings
export EMBEDDING_API_KEY=your_key
export EMBEDDING_PROVIDER=chutes-0.6b
```

### Docker Deployment

```bash
cd tweet-graph-system

# Configure
cp .env.example .env
# Edit .env with your keys

# Start services
docker-compose up -d

# Services:
# - API: http://localhost:8000
# - Portal: http://localhost:3000
# - Neo4j: bolt://localhost:7687 (neo4j/tweetgraph123)
```

### Install Skill

```bash
cp -r openclaw-skill-tweet-graph ~/.openclaw/skills/tweet-graph
# Restart OpenClaw
```

## Usage

### Search Tweets (Semantic)

```
find tweets about: machine learning
search for tweets about: AI agents
/tweets about crypto
```

### Store a Tweet

From URL:
```
store this tweet: https://x.com/user/status/123456789
```

Manual entry:
```
store tweet:
id: manual-001
text: "This is a manually stored tweet #example @user"
author: myuser
```

### Sync X Bookmarks

```
sync my X bookmarks
fetch my bookmarks
/sync
```

### Get Related Tweets

```
show related to tweet: 123456789
what's connected to: abc123
```

### Theme & Entity Exploration

```
show me themes in my tweets
what entities have been mentioned?
/themes
```

### Statistics

```
tweet graph stats
/stats
```

### Open Portal

```
open tweet graph
/graph
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Health check |
| `GET` | `/stats` | Database statistics |
| `POST` | `/tweets` | Store a tweet |
| `GET` | `/tweets/{id}` | Get tweet by ID |
| `GET` | `/tweets` | Get all tweets |
| `POST` | `/search` | Vector similarity search |
| `POST` | `/related` | Graph traversal query |
| `POST` | `/bookmarks/sync` | Bulk import bookmarks |
| `GET` | `/graph` | Graph data for visualization |
| `GET` | `/themes` | All themes with counts |
| `GET` | `/entities` | All entities with counts |

## Web Portal

Access at http://localhost:3000:

| Page | Description |
|------|-------------|
| `/` | Dashboard with stats |
| `/graph` | Interactive force-directed graph |
| `/search` | Semantic search with similarity scores |
| `/tweets` | Tweet browser with embeds |
| `/themes` | Theme and entity explorer |

## Graph Schema

```
# Core Relationships
(:User)-[:POSTED]->(:Tweet)
(:Tweet)-[:HAS_HASHTAG]->(:Hashtag)
(:Tweet)-[:MENTIONS]->(:User)
(:Tweet)-[:CONTAINS_URL]->(:URL)

# Theme & Entity Extraction
(:Tweet)-[:ABOUT_THEME]->(:Theme)
(:Tweet)-[:MENTIONS_ENTITY]->(:Entity)
```

## Examples

**User:** `/search AI agents`

**Assistant:** Found 8 tweets about "AI agents":

1. **@karpathy** [94% match]
   "New art project. Train and inference GPT in 243 lines of pure, dependency-free Python..."
   Themes: ai, dev | Entities: GPT, Python

2. **@techNmak** [87% match]
   "The person who built Claude Code just mass-leaked the thinking prompts..."
   Themes: ai, llm | Entities: Claude, Anthropic
...

---

**User:** `/themes`

**Assistant:** Themes in your tweets:
- **ai**: 15 tweets
- **llm**: 8 tweets
- **dev**: 6 tweets
- **crypto**: 4 tweets
- **business**: 3 tweets

---

**User:** `/sync`

**Assistant:** Syncing X bookmarks...
✅ Synced 12 bookmarks
- New: 5
- Updated: 3
- Duplicates: 4
- Enriched: 2 (via X API v2)

---

**User:** `/stats`

**Assistant:** Tweet Graph Stats:
- **Tweets**: 47
- **Users**: 32
- **Hashtags**: 18
- **Themes**: 5
- **Entities**: 42
- **Relationships**: 156
- **Embedding Provider**: chutes-0.6b (1024 dims)

## Truncation Detection

The system automatically detects truncated tweets:
- Browser-scraped tweets marked as `truncated: true`
- X API v2 enrichment sets `truncated: false`
- Hybrid mode: browser fetch + API fix

## Troubleshooting

**Browser fetch hangs:**
- Restart Chrome and relay after OpenClaw upgrades

**Missing authors:**
- Re-run bookmark fetcher

**Truncated tweets:**
- Set `TWITTER_BEARER_TOKEN` for X API v2

## Project Location

```
~/.openclaw/workspace/tweet-graph-system/
```

## License

MIT License - Open Source
