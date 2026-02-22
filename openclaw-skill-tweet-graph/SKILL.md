---
name: tweet-graph
description: Store and search tweets in Neo4j graph database with semantic search and theme extraction
user-invocable: true
metadata: {"openclaw": {"emoji": "🐦"}}
---

# Tweet Graph Skill

Store and retrieve tweets in a Neo4j graph database with automatic entity extraction, theme detection, and web portal visualization.

## Quick Commands

| Command | Description |
|---------|-------------|
| `/tweets` | Show latest tweets |
| `/search <query>` | Search tweets semantically |
| `/themes` | Show all themes |
| `/stats` | Database statistics |
| `/graph` | Show portal URL |

## Natural Language Commands

- `find tweets about: [query]` - Semantic search
- `search for tweets about: [query]` - Alternative search
- `store this tweet: [url]` - Store from URL
- `show themes` - List detected themes
- `tweet graph stats` - Show statistics
- `open tweet graph` - Get portal URL

## API Configuration

The skill uses the Tweet Graph API. Set environment variable:
- `TWEET_GRAPH_API_URL` - Default: `http://localhost:8000`

## Implementation

When the user asks to search or manage tweets, use the `exec` tool to call the API:

### Search Tweets
```bash
curl -s -X POST ${TWEET_GRAPH_API_URL:-http://localhost:8000}/search \
  -H "Content-Type: application/json" \
  -d '{"query": "<USER_QUERY>", "limit": 10}' | jq .
```

### Get Stats
```bash
curl -s ${TWEET_GRAPH_API_URL:-http://localhost:8000}/stats | jq .
```

### Get All Tweets
```bash
curl -s ${TWEET_GRAPH_API_URL:-http://localhost:8000}/tweets | jq .
```

### Get Themes
```bash
curl -s ${TWEET_GRAPH_API_URL:-http://localhost:8000}/themes | jq .
```

### Get Entities
```bash
curl -s ${TWEET_GRAPH_API_URL:-http://localhost:8000}/entities | jq .
```

### Store Tweet
```bash
curl -s -X POST ${TWEET_GRAPH_API_URL:-http://localhost:8000}/tweets \
  -H "Content-Type: application/json" \
  -d '{"id": "<TWEET_ID>", "text": "<TEXT>", "author_username": "<AUTHOR>"}' | jq .
```

## Response Formatting

When showing results, format nicely:
- Use **bold** for authors
- Use `code` for tweet IDs
- Show similarity scores as percentages
- List themes with 🎯 emoji

## Portal

The web portal is available at: http://localhost:3000

Pages:
- `/` - Dashboard with stats
- `/graph` - Interactive graph visualization
- `/search` - Semantic search interface
- `/tweets` - Tweet browser
- `/themes` - Theme explorer

## Example Responses

**Search result:**
```
Found 5 tweets about "AI agents":

1. [92%] @karpathy: "New art project. Train and inference GPT in 243 lines..."
   🎯 ai, dev

2. [87%] @techNmak: "The person who built Claude Code just mass-leaked..."
   🎯 ai, llm
```

**Stats:**
```
📊 Tweet Graph Stats

📝 Tweets: 47
👤 Users: 32
#️⃣ Hashtags: 18
🎯 Themes: 5
🔗 Relationships: 156
```

## Project Location

```
~/.openclaw/workspace/tweet-graph-system/
```

## Notes

- The API must be running (docker-compose up -d)
- Semantic search uses vector embeddings
- Themes are auto-detected: ai, llm, dev, crypto, business
- Entities are proper nouns extracted from text
