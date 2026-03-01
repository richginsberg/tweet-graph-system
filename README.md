# Tweet Graph System

> Store, search, and explore tweets in a Neo4j graph database with vector embeddings and OpenClaw integration

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Docker](https://img.shields.io/badge/Docker-Ready-blue)](https://www.docker.com/)
[![Kubernetes](https://img.shields.io/badge/Kubernetes-Ready-blue)](https://kubernetes.io/)

A complete system for storing tweets in a graph database, performing semantic search with vector embeddings, and automatically syncing your X/Twitter bookmarks.

---

## Features

- **📊 Graph Storage** - Store tweets with automatic entity extraction (users, hashtags, URLs, mentions)
- **🔍 Semantic Search** - Vector similarity search powered by embeddings
- **🔗 Relationship Queries** - Graph traversal for finding related content
- **🤖 Multi-Provider Support** - Works with OpenAI, DeepSeek, Together AI, Groq, Ollama, or any OpenAI-compatible API
- **📱 OpenClaw Skill** - Natural language commands to store and search tweets
- **🔄 Bookmark Sync** - Daily cron job to fetch and store your X/Twitter bookmarks
- **🐦 X API v2 Integration** - Fix truncated posts with hybrid mode (browser + API)
- **📖 Truncated Post Labels** - Automatic detection and labeling of incomplete tweets
- **🐳 Easy Deployment** - Docker Compose for local, Kubernetes for production
- **📊 Web Portal** - Next.js dashboard with graph visualization and search
- **🏷️ Theme Extraction** - Automatic detection of AI, crypto, dev, business themes
- **👤 Entity Recognition** - Extract proper nouns and create relationships

---

## Table of Contents

- [Quick Start](#quick-start)
- [Architecture](#architecture)
- [Deployment](#deployment)
  - [Docker Compose (Local)](#option-1-docker-compose-local)
  - [Kubernetes (Production)](#option-2-kubernetes-production)
- [Configuration](#configuration)
  - [Embedding Providers](#embedding-providers)
- [API Reference](#api-reference)
- [OpenClaw Skill](#openclaw-skill)
- [Examples](#examples)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)
- [License](#license)

---

## Quick Start

### Prerequisites

- Docker and Docker Compose (for local deployment)
- OR Kubernetes cluster (for production)
- API key for an embedding provider (OpenAI, DeepSeek, etc.)

### 30-Second Setup

```bash
# Clone the repository
git clone https://github.com/yourusername/tweet-graph-system.git
cd tweet-graph-system

# Configure your secrets (choose one method)

# Method 1: .env file (recommended)
cp .env.example .env
# Edit .env and add your API keys

# Method 2: Docker override (keeps secrets outside .env)
cp docker-compose.override.yml.example docker-compose.override.yml
# Edit docker-compose.override.yml and add your secrets

# Method 3: Environment variables (from .bashrc, CI/CD, etc.)
# Just run docker-compose - it will pick them up automatically

# Start services
docker-compose up -d

# Test
curl http://localhost:8000/health
```

**Services:**
- 🌐 Neo4j Browser: http://localhost:7474
- 🚀 Tweet Graph API: http://localhost:8000
- 📊 Web Portal: http://localhost:3000
- 📖 API Documentation: http://localhost:8000/docs

**Default Credentials:**
- Neo4j: `neo4j` / `tweetgraph123` (change in production!)

### Secret Management

This project follows security best practices:

| File | Purpose | Git Status |
|------|---------|------------|
| `.env.example` | Template with placeholders | ✅ Committed |
| `.env` | Your real secrets | ❌ Gitignored |
| `docker-compose.override.yml` | Local Docker overrides | ❌ Gitignored |
| `docker-compose.yml` | Uses `${VAR:-default}` syntax | ✅ Committed (safe) |

**Never commit real API keys or tokens!**

---

## Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  Browser Relay  │────▶│  Bookmark Fetcher │────▶│                 │
│  (Chrome X)     │     │  (Daily Cron)      │     │     Neo4j       │
└─────────────────┘     └──────────────────┘     │   (Graph DB)    │
                                 │               │                 │
                        ┌────────┴────────┐      │                 │
                        │                 │      │                 │
                        ▼                 ▼      │                 │
                   ┌─────────┐     ┌──────────┐  │                 │
                   │ Browser │     │ X API v2 │  │                 │
                   │ Scrape  │     │ (Hybrid) │  │                 │
                   └─────────┘     └──────────┘  │                 │
                                                 │                 │
┌─────────────────┐     ┌──────────────────┐     │                 │
│  OpenClaw Skill │────▶│  Tweet Graph API  │────▶│                 │
│  (Manual Store) │     │  (FastAPI)        │     │                 │
└─────────────────┘     └──────────────────┘     └─────────────────┘
                                │
                                │
        ┌───────────────────────┼───────────────────────┐
                        ┌───────┴───────┐
                        │               │
                        ▼               ▼
                ┌──────────────────┐    ┌──────────────────┐
                │ Embedding Provider│    │   Web Portal     │
                │ (OpenAI/DeepSeek/ │    │   (Next.js)      │
                │  Together/Groq/   │    │                  │
                │  Chutes/Ollama)   │    │  • Dashboard     │
                └──────────────────┘    │  • Graph View    │
                                        │  • Search        │
                        ┌───────────────│  • Themes        │
                        │               └──────────────────┘
                        ▼
                 ┌─────────────┐
                 │   Browser   │
                 │ (Local/LAN) │
                 └─────────────┘
```

### Components

| Component | Technology | Purpose |
|-----------|------------|---------|
| **Neo4j** | Graph Database 5.15 | Store tweets, users, hashtags, relationships |
| **Tweet Graph API** | FastAPI + Python | REST API for storage/retrieval |
| **Web Portal** | Next.js 14 + React | Visual dashboard and graph explorer |
| **Embedding Provider** | OpenAI/Chutes/etc | Vector embeddings for semantic search |
| **OpenClaw Skill** | Python | Natural language interface |
| **Bookmark Fetcher** | Python CronJob | Automated X bookmarks sync |

### Graph Schema

```
# Core Relationships
(:User)-[:POSTED]->(:Tweet)
(:Tweet)-[:HAS_HASHTAG]->(:Hashtag)
(:Tweet)-[:MENTIONS]->(:User)
(:Tweet)-[:REPLY_TO]->(:Tweet)
(:Tweet)-[:QUOTES]->(:Tweet)
(:Tweet)-[:CONTAINS_URL]->(:URL)

# Theme & Entity Extraction
(:Tweet)-[:ABOUT_THEME]->(:Theme)
(:Tweet)-[:MENTIONS_ENTITY]->(:Entity)
```

---

## Deployment

### Option 1: Docker Compose (Local)

**Best for:** Development, testing, single-server deployment

```bash
# 1. Configure
cp .env.example .env
vim .env  # Add your API key

# 2. Start services
./start.sh
# Or manually: docker-compose up -d

# 3. Verify
curl http://localhost:8000/health
```

**Useful Commands:**

```bash
# View logs
docker-compose logs -f api
docker-compose logs -f neo4j

# Stop services
./stop.sh
# Or: docker-compose down

# Reset all data
docker-compose down -v

# Restart API only
docker-compose restart api
```

**Port Configuration:**

If ports are in use, edit `docker-compose.yml`:

```yaml
services:
  neo4j:
    ports:
      - "17474:7474"  # Change HTTP port
      - "17687:7687"  # Change Bolt port
  api:
    ports:
      - "18000:8000"  # Change API port
```

---

### Option 2: Kubernetes (Production)

**Best for:** Production, scaling, high availability

#### Quick Deploy

```bash
# 1. Create namespace and secrets
kubectl apply -f k8s/namespace.yaml

kubectl create secret generic tweet-graph-secrets \
  --from-literal=EMBEDDING_API_KEY=your-api-key \
  -n tweet-graph

# 2. Deploy all components
kubectl apply -k k8s/

# 3. Wait for pods
kubectl wait --for=condition=ready pod -l app.kubernetes.io/name=neo4j -n tweet-graph --timeout=300s
kubectl wait --for=condition=ready pod -l app.kubernetes.io/name=tweet-graph-api -n tweet-graph --timeout=300s

# 4. Verify
kubectl get pods -n tweet-graph
```

#### Configure Provider

```bash
# Update embedding provider
kubectl set env deployment/tweet-graph-api \
  EMBEDDING_PROVIDER=deepseek \
  EMBEDDING_MODEL=deepseek-embed \
  -n tweet-graph

# Update API key
kubectl create secret generic tweet-graph-secrets \
  --from-literal=EMBEDDING_API_KEY=new-key \
  -n tweet-graph --dry-run=client -o yaml | kubectl apply -f -
```

#### Access Services

```bash
# Port-forward Neo4j Browser
kubectl port-forward svc/neo4j 7474:7474 -n tweet-graph

# Port-forward API
kubectl port-forward svc/tweet-graph-api 8000:8000 -n tweet-graph

# Or use ingress (if configured)
# http://neo4j.yourdomain.com
# http://api.yourdomain.com
```

#### Scaling

```bash
# Scale API
kubectl scale deployment tweet-graph-api --replicas=3 -n tweet-graph

# View resource usage
kubectl top pods -n tweet-graph
```

#### Cleanup

```bash
# Delete namespace (removes everything)
kubectl delete namespace tweet-graph
```

---

## Configuration

### Embedding Providers

The system supports any OpenAI-compatible embedding API:

| Provider | Cost (1M tokens) | Models | Dimensions | Setup |
|----------|-----------------|--------|------------|-------|
| **OpenAI** | $0.02 | text-embedding-3-small, text-embedding-3-large | 1536, 3072 | Default |
| **DeepInfra** | ~$0.0001 | Qwen/Qwen3-Embedding-0.6B, Qwen/Qwen3-Embedding-0.6B-batch | 1024 | Cheap + Fast |
| **Chutes.ai (8B)** | Varies | qwen3-embedding-8b | 4096 | High Quality |
| **Chutes.ai (0.6B)** | Varies | qwen3-embedding-0.6b | 1024 | Fast |
| **DeepSeek** | $0.001 | deepseek-embed | 1536 | Very Cheap |
| **Together AI** | $0.0001 | m2-bert-80M-8k-retrieval | 768 | Ultra cheap |
| **Groq** | Free tier | nomic-embed-text-v1 | 768 | Fast |
| **Ollama** | Free | nomic-embed-text, all-minilm | 768, 384 | Local |
| **Custom** | Varies | Any OpenAI-compatible | Configurable | Flexible |

### Provider Configuration

#### OpenAI (Default)

```bash
EMBEDDING_PROVIDER=openai
EMBEDDING_API_KEY=sk-your-openai-key
EMBEDDING_MODEL=text-embedding-3-small
EMBEDDING_DIMENSIONS=1536
```

#### DeepInfra (Qwen3 Embeddings - Recommended)

DeepInfra offers Qwen3 embeddings with single and batch modes:

```bash
# Single mode (for individual tweets)
EMBEDDING_PROVIDER=deepinfra
EMBEDDING_PROVIDER_ACTIVE=single
EMBEDDING_API_KEY=your-deepinfra-key
EMBEDDING_DIMENSIONS=1024

# Batch mode (for bulk imports - faster)
EMBEDDING_PROVIDER=deepinfra
EMBEDDING_PROVIDER_ACTIVE=batch
EMBEDDING_API_KEY=your-deepinfra-key
EMBEDDING_DIMENSIONS=1024
```

**Explicit single/batch providers:**

```bash
# Explicit single
EMBEDDING_PROVIDER=deepinfra-single
EMBEDDING_API_KEY=your-deepinfra-key
EMBEDDING_DIMENSIONS=1024

# Explicit batch
EMBEDDING_PROVIDER=deepinfra-batch
EMBEDDING_API_KEY=your-deepinfra-key
EMBEDDING_DIMENSIONS=1024
```

**API endpoints:**
- Single: `Qwen/Qwen3-Embedding-0.6B`
- Batch: `Qwen/Qwen3-Embedding-0.6B-batch`
- Both use: `https://api.deepinfra.com/v1/openai/embeddings`

#### DeepSeek

```bash
EMBEDDING_PROVIDER=deepseek
EMBEDDING_API_KEY=your-deepseek-key
EMBEDDING_MODEL=deepseek-embed
EMBEDDING_DIMENSIONS=1536
```

#### Together AI

```bash
EMBEDDING_PROVIDER=together
EMBEDDING_API_KEY=your-together-key
EMBEDDING_MODEL=togethercomputer/m2-bert-80M-8k-retrieval
EMBEDDING_DIMENSIONS=768
```

#### Groq

```bash
EMBEDDING_PROVIDER=groq
EMBEDDING_API_KEY=your-groq-key
EMBEDDING_MODEL=nomic-embed-text-v1
EMBEDDING_DIMENSIONS=768
```

#### Ollama (Local)

First, install and run Ollama:

```bash
# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Pull embedding model
ollama pull nomic-embed-text

# Run Ollama server
ollama serve
```

Then configure:

```bash
EMBEDDING_PROVIDER=ollama
EMBEDDING_API_BASE=http://host.docker.internal:11434/v1  # Docker
# EMBEDDING_API_BASE=http://localhost:11434/v1  # Local
EMBEDDING_MODEL=nomic-embed-text
EMBEDDING_DIMENSIONS=768
```

#### Custom Provider

Any OpenAI-compatible API:

```bash
EMBEDDING_PROVIDER=custom
EMBEDDING_API_BASE=https://your-api.com/v1
EMBEDDING_API_KEY=your-key
EMBEDDING_MODEL=your-model
EMBEDDING_DIMENSIONS=1536
```

### NER Providers (Named Entity Recognition)

The system extracts named entities (people, organizations, locations) from tweets. Choose a provider based on your hardware:

| Provider | Size | Speed | Accuracy | Zero-shot | Best For |
|----------|------|-------|----------|-----------|----------|
| **regex** | 0MB | Instant | Low | ❌ | Low-end CPU (default) |
| **spacy-sm** | ~13MB | Fast | Good | ❌ | Most users |
| **spacy-lg** | ~700MB | Fast | Better | ❌ | Better accuracy |
| **gliner-small** | ~120MB | Medium | Good | ✅ | Custom entity types |
| **gliner-medium** | ~300MB | Slower | Better | ✅ | Zero-shot NER |
| **minibase** | ~369MB | 323ms | 91.5% P, 100% R | ❌ | High recall |
| **disabled** | 0MB | Instant | N/A | N/A | Disable extraction |

#### Regex (Default - No Dependencies)

Works on any CPU, no installation required:

```bash
NER_PROVIDER=regex
```

> ⚠️ **Note:** Regex has many false positives (any capitalized word). For better accuracy, use spaCy.

#### spaCy (Recommended)

Fast and accurate entity extraction:

```bash
# Install spaCy and download model
pip install spacy
python -m spacy download en_core_web_sm

# Configure
NER_PROVIDER=spacy-sm   # Fast, ~13MB
# NER_PROVIDER=spacy-lg # More accurate, ~700MB
```

**Entity types extracted:** PERSON, ORG, GPE, PRODUCT, EVENT, LOC

#### GLiNER (Zero-shot NER)

Extract any entity type with natural language prompts:

```bash
# Install GLiNER
pip install gliner

# Configure
NER_PROVIDER=gliner-small   # ~120MB
# NER_PROVIDER=gliner-medium # ~300MB, better accuracy

# Optional: Custom entity labels
NER_LABELS=person,organization,company,product,technology,location,event
```

**Advantages:**
- Extract any entity type (not limited to predefined categories)
- Zero-shot: no training needed
- Good for domain-specific entities

#### Minibase (High Recall)

High precision (91.5%) and perfect recall (100%):

```bash
# Install transformers
pip install transformers torch

# Configure
NER_PROVIDER=minibase
```

**Entity types:** PER, ORG, LOC, MISC

#### Disable Entity Extraction

To disable entity extraction entirely:

```bash
NER_PROVIDER=disabled
```

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `EMBEDDING_PROVIDER` | Provider name | `openai` |
| `EMBEDDING_PROVIDER_ACTIVE` | Mode for providers with single/batch | `single` |
| `EMBEDDING_API_KEY` | API key | - |
| `EMBEDDING_API_BASE` | Custom API URL | Provider default |
| `EMBEDDING_MODEL` | Model name | `text-embedding-3-small` |
| `EMBEDDING_DIMENSIONS` | Vector dimensions | `1536` |
| `NER_PROVIDER` | Named Entity Recognition provider | `regex` |
| `NER_LABELS` | Custom labels for GLiNER (comma-separated) | - |
| `NEO4J_URI` | Neo4j connection | `bolt://neo4j:7687` |
| `NEO4J_USER` | Neo4j username | `neo4j` |
| `NEO4J_PASSWORD` | Neo4j password | `tweetgraph123` |
| `FETCH_MODE` | Bookmark fetch mode | `browser` |
| `X_BEARER_TOKEN` | X API v2 bearer token | - |
| `TRUNCATION_INDICATORS` | Truncation detection chars | `…,>>>,[more]` |

---

## Web Portal

The Tweet Graph Portal is a Next.js application for visualizing and exploring your tweet graph.

### Features

- **📊 Dashboard** - Overview stats with quick navigation
- **🕸️ Graph Visualization** - Interactive force-directed graph (react-force-graph)
- **🔍 Semantic Search** - Find tweets by meaning, not just keywords
- **📝 Tweet Browser** - Browse all stored tweets with filters
- **🏷️ Themes & Entities** - Explore extracted topics and proper nouns

### Running Locally

```bash
cd portal

# Install dependencies
npm install

# Development server
npm run dev

# Access at http://localhost:3000
```

### Building for Production

```bash
# Build standalone
npm run build

# Start production server
npm start
```

### Docker Build

```bash
# Build image
docker build -t tweet-graph-portal:latest ./portal

# Run container
docker run -p 3000:3000 \
  -e NEXT_PUBLIC_API_URL=http://your-api-host:8000 \
  tweet-graph-portal:latest
```

### Portal Pages

| Route | Description |
|-------|-------------|
| `/` | Dashboard with stats overview |
| `/graph` | Interactive graph visualization |
| `/search` | Semantic search interface |
| `/tweets` | Browse all stored tweets |
| `/themes` | Themes and entities explorer |

### Configuration

The Portal automatically detects the API URL based on how you access it:
- Access via `localhost:3000` → API at `localhost:8000`
- Access via `192.168.x.x:3000` → API at `192.168.x.x:8000`

No manual configuration needed for LAN access. The browser uses the same hostname as the Portal.

For custom deployments, set via environment variable:

```bash
# Docker Compose
environment:
  - NEXT_PUBLIC_API_URL=http://your-api-host:8000
  - API_URL=http://api:8000  # For SSR (Docker internal)
```

---

## API Reference

### Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Health check |
| `GET` | `/stats` | Database statistics |
| `GET` | `/config` | Current configuration |
| `POST` | `/tweets` | Store a tweet |
| `GET` | `/tweets/{id}` | Get tweet by ID |
| `GET` | `/tweets` | Get all tweets |
| `GET` | `/tweets/truncated` | Get truncated tweets needing enrichment |
| `DELETE` | `/tweets/all` | Clear all tweets (keeps other nodes) |
| `DELETE` | `/database/all` | Clear ALL data from database |
| `POST` | `/search` | Vector similarity search |
| `POST` | `/related` | Graph traversal query |
| `POST` | `/bookmarks/sync` | Bulk import bookmarks |
| `GET` | `/graph` | Graph data for visualization |
| `GET` | `/themes` | All themes with counts |
| `GET` | `/entities` | All entities with counts |

### Store Tweet

```bash
POST /tweets
Content-Type: application/json

{
  "id": "123456789",
  "text": "Machine learning is transforming #AI @openai https://example.com",
  "author_id": "user123",
  "author_username": "testuser",
  "hashtags": ["AI"],
  "mentions": ["openai"],
  "urls": ["https://example.com"],
  "reply_to": "987654321",     // Optional: reply parent
  "quote_of": "111222333",     // Optional: quoted tweet
  "bookmark_url": "https://twitter.com/..."  // Optional
}
```

**Response:**

```json
{
  "id": "123456789",
  "text": "Machine learning is transforming #AI...",
  "stored": true,
  "message": "Tweet stored successfully",
  "related_count": 5
}
```

### Search Tweets

```bash
POST /search
Content-Type: application/json

{
  "query": "artificial intelligence and machine learning",
  "limit": 10
}
```

**Response:**

```json
{
  "query": "artificial intelligence and machine learning",
  "results": [
    {
      "id": "123456789",
      "text": "Machine learning is transforming #AI...",
      "author": "testuser",
      "score": 0.92,
      "hashtags": ["AI"]
    }
  ],
  "count": 1
}
```

### Get Related

```bash
POST /related
Content-Type: application/json

{
  "tweet_id": "123456789",
  "depth": 2,
  "relationship_types": ["HAS_HASHTAG", "MENTIONS"]  // Optional filter
}
```

**Response:**

```json
{
  "tweet_id": "123456789",
  "related": [
    {
      "type": "Hashtag",
      "id": "ai",
      "properties": {"tag": "AI"},
      "relationship": "HAS_HASHTAG"
    },
    {
      "type": "User",
      "id": "openai",
      "properties": {"username": "openai"},
      "relationship": "MENTIONS"
    }
  ],
  "count": 2
}
```

### Bulk Import

```bash
POST /bookmarks/sync
Content-Type: application/json

{
  "bookmarks": [
    {"id": "1", "text": "Tweet 1", ...},
    {"id": "2", "text": "Tweet 2", ...}
  ]
}
```

**Response:**

```json
{
  "total_received": 2,
  "new_stored": 1,
  "duplicates_skipped": 1
}
```

---

## OpenClaw Skill

### Installation

```bash
# Copy skill to OpenClaw skills directory
cp -r openclaw-skill-tweet-graph ~/.openclaw/skills/tweet-graph

# Restart OpenClaw
```

### Configuration

Set environment variable:

```bash
export TWEET_GRAPH_API_URL=http://localhost:8000
```

Or add to your OpenClaw configuration.

### X/Twitter Authentication (for Bookmark Fetcher)

The bookmark fetcher supports two authentication methods:

#### Option A: Browser Relay

If you have a paired node with Chrome:
1. Log into X.com in Chrome on the paired node
2. The fetcher navigates to bookmarks using your existing session
3. Session cookies handle authentication automatically

#### Option B: Playwright + Cookies (Local)

**Step 1: Export cookies from Chrome**

1. Install **EditThisCookie** or **Cookie Editor** extension
2. Go to https://x.com and log in
3. Click extension → Export cookies → JSON
4. Save to: `bookmark-fetcher/cookies.json`

**Step 2: Install dependencies**

> ⚠️ **Python Version:** Python 3.11-3.12 is recommended. Python 3.14+ may have compatibility issues with Playwright's bundled Node.js. If you encounter `EPIPE` errors, use Python 3.11 or run via Docker.

```bash
# Navigate to bookmark-fetcher
cd tweet-graph-system/bookmark-fetcher

# Create virtual environment (use Python 3.11 if available)
python3.11 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements-playwright.txt
playwright install chromium
```

**Step 3: Run**

```bash
# Navigate to bookmark-fetcher and activate venv
cd tweet-graph-system/bookmark-fetcher
source venv/bin/activate

# Set API URL
export TWEET_GRAPH_API_URL=http://localhost:8000

# Run fetcher
python -m fetcher.main_playwright
```

**Cookie format:**

```json
[
  {"name": "auth_token", "value": "xxx", "domain": ".x.com"},
  {"name": "ct0", "value": "xxx", "domain": ".x.com"},
  {"name": "guest_id", "value": "xxx", "domain": ".x.com"}
]
```

**Key cookies needed:**
- `auth_token` - Main authentication
- `ct0` - CSRF token

> ⚠️ **Important:** Add `cookies.json` to `.gitignore` (already included) to avoid committing credentials.

#### Daily Cron Job (Automatic Sync)

To automatically fetch bookmarks daily:

**Step 1: Create cron script**

```bash
cd tweet-graph-system/scripts
chmod +x fetch-bookmarks-cron.sh
```

**Step 2: Edit the script to match your paths**

```bash
#!/bin/bash
# Update this path to match your installation
cd /path/to/tweet-graph-system/bookmark-fetcher
source venv/bin/activate
export TWEET_GRAPH_API_URL=http://localhost:8000
python -m fetcher.main_playwright
echo "$(date): Fetch completed" >> /var/log/tweet-graph.log
```

**Step 3: Add to crontab**

```bash
crontab -e

# Add this line (runs daily at 6 AM)
0 6 * * * /path/to/tweet-graph-system/scripts/fetch-bookmarks-cron.sh
```

**Cron schedule examples:**

| Schedule | Cron expression |
|----------|-----------------|
| Daily at 6 AM | `0 6 * * *` |
| Every 12 hours | `0 */12 * * *` |
| Every hour | `0 * * * *` |
| Daily at midnight | `0 0 * * *` |

**View cron logs:**

```bash
cat /var/log/tweet-graph.log
```

---

## 🤖 Automatic Processing

**Good news:** Everything is automatic! When you sync bookmarks, the system automatically:

1. **Extracts Themes** - AI, LLM, crypto, dev, business, etc. (keyword-based)
2. **Extracts Entities** - Proper nouns like "Elon Musk", "OpenAI", "Sam Altman"
3. **Extracts Hashtags** - From tweet text
4. **Extracts Mentions** - @usernames
5. **Generates Embeddings** - For semantic search
6. **Detects Truncation** - Marks incomplete tweets

No manual pipelines needed. Just run the bookmark sync and everything is populated.

### Initial Setup (One-Time)

```bash
# 1. Start services
docker-compose up -d

# 2. Configure X/Twitter cookies (see Authentication section)

# 3. Run initial full import
cd bookmark-fetcher
source venv/bin/activate
python -m fetcher.main_playwright --full

# 4. (Optional) Set up cron jobs for daily sync
```

### Daily Automation

Once cron jobs are set up (see [Automated Maintenance](#automated-maintenance)), the system:
- **Daily:** Fetches new bookmarks, extracts themes/entities, generates embeddings
- **Monthly:** Enriches truncated tweets via X API v2 (if token configured)

### What Gets Populated

| Data | Source | Automatic? |
|------|--------|------------|
| Tweets | X/Twitter bookmarks | ✅ On sync |
| Themes | Keyword extraction | ✅ On store |
| Entities | Proper noun extraction | ✅ On store |
| Hashtags | From tweet text | ✅ On store |
| Mentions | @usernames | ✅ On store |
| Embeddings | Configured provider | ✅ On store |
| Truncation | Auto-detected | ✅ On store |

---

## Automated Maintenance

This project includes cron scripts for automated maintenance. These are essential for:
- **Daily incremental sync** - Keep bookmarks up to date
- **Monthly truncation enrichment** - Fix truncated posts when X API credits reset

### Available Scripts

| Script | Purpose | Recommended Schedule |
|--------|---------|---------------------|
| `scripts/cron-daily-sync.sh` | Fetch new bookmarks | Daily at 6 AM |
| `scripts/cron-monthly-enrich.sh` | Enrich truncated tweets via X API | 1st of month at 3 AM |

### Setup (OpenClaw Gateway)

If using OpenClaw, the easiest way is to use the built-in cron system:

```bash
# Daily bookmark sync (every day at 6 AM)
openclaw cron add \
  --name "tweet-graph-daily-sync" \
  --schedule "0 6 * * *" \
  --session-target main \
  --payload '{"kind": "systemEvent", "text": "Run tweet graph daily sync: cd ~/.openclaw/workspace/workspace/tweet-graph-system && ./scripts/cron-daily-sync.sh"}'

# Monthly enrichment (1st of each month at 3 AM)
openclaw cron add \
  --name "tweet-graph-monthly-enrich" \
  --schedule "0 3 1 * *" \
  --session-target main \
  --payload '{"kind": "systemEvent", "text": "Run tweet graph monthly enrichment: cd ~/.openclaw/workspace/workspace/tweet-graph-system && TWITTER_BEARER_TOKEN=$TWITTER_BEARER_TOKEN ./scripts/cron-monthly-enrich.sh"}'
```

### Setup (Traditional Crontab)

For standard Linux cron:

```bash
# Edit crontab
crontab -e

# Add these lines:
# Daily sync at 6 AM
0 6 * * * /path/to/tweet-graph-system/scripts/cron-daily-sync.sh >> /var/log/tweet-graph-sync.log 2>&1

# Monthly enrichment on 1st at 3 AM
0 3 1 * * TWITTER_BEARER_TOKEN=your_token /path/to/tweet-graph-system/scripts/cron-monthly-enrich.sh >> /var/log/tweet-graph-enrich.log 2>&1
```

### Query Truncated Tweets

Check how many tweets need enrichment:

```bash
# Via API
curl http://localhost:8000/tweets/truncated | jq '.count'

# Detailed list
curl http://localhost:8000/tweets/truncated | jq '.tweets[]'
```

### Clear Database (Fresh Import)

To start fresh with a clean import:

```bash
# Clear all tweets (keeps users, hashtags, etc.)
curl -X DELETE http://localhost:8000/tweets/all

# Nuclear option: clear EVERYTHING
curl -X DELETE http://localhost:8000/database/all
```

### Recommended Workflow

1. **Initial Setup:** Clear database → Full import
2. **Daily:** Cron runs `cron-daily-sync.sh` for incremental bookmarks
3. **Monthly:** Cron runs `cron-monthly-enrich.sh` to fix truncated posts

#### Fetch Modes & Truncated Post Handling

The bookmark fetcher supports three modes for handling tweet content:

| Mode | Description | Best For |
|------|-------------|----------|
| `browser` | Browser scraping only, marks truncated tweets | No API setup needed |
| `api` | X API v2 only (for low usage) | Users with X developer access |
| `hybrid` | Browser + API to fix truncated tweets | Best experience (recommended) |

**Configure fetch mode:**

```bash
# In .env or environment
FETCH_MODE=browser   # Default: browser only
FETCH_MODE=hybrid    # Recommended: browser + API
FETCH_MODE=api       # API only (requires credentials)
```

**Truncated posts** are automatically detected and labeled:

```
📖 [TRUNCATED - click bookmark for full text]

Original truncated text...
```

They're also tagged with `__truncated__` for easy filtering.

**X API v2 Setup (for hybrid/api modes):**

1. Go to https://developer.twitter.com/en/portal/dashboard
2. Create a project & app (Free tier: 1,500 posts/month)
3. Generate Bearer Token
4. Configure:

```bash
# In .env
FETCH_MODE=hybrid
X_BEARER_TOKEN=your_bearer_token_here
```

**Customize truncation detection:**

```bash
# Comma-separated indicators
TRUNCATION_INDICATORS=…,>>>,[more],…
```

**Run with hybrid mode:**

```bash
cd bookmark-fetcher
source venv/bin/activate
export FETCH_MODE=hybrid
export X_BEARER_TOKEN=your_token
python -m fetcher.main_hybrid
```

### Commands

| Command | Description | Example |
|---------|-------------|---------|
| `store this tweet: [url]` | Store from URL | `store this tweet: https://twitter.com/user/status/123` |
| `find tweets about: [query]` | Vector search | `find tweets about: machine learning` |
| `search for tweets about: [query]` | Vector search | `search for tweets about: AI safety` |
| `show related to tweet: [id]` | Graph traversal | `show related to tweet: 123456` |
| `what's connected to: [id]` | Graph traversal | `what's connected to: 123456` |
| `tweet graph stats` | Statistics | `tweet graph stats` |

### Example Usage

**User:** `store this tweet: https://twitter.com/elonmusk/status/123456`

**Assistant:**
```
✅ Tweet stored successfully!
- ID: 123456
- Author: @elonmusk
- Hashtags: #SpaceX, #Mars
- Mentions: @NASA
- Relationships created: 5
```

**User:** `find tweets about: space exploration`

**Assistant:**
```
Found 8 related tweets:

1. [Score: 0.94] "Mars colonization will require..." by @SpaceXFan
2. [Score: 0.89] "The path to Mars goes through..." by @ElonMusk
3. [Score: 0.85] "Space exploration is humanity's..." by @NeilTyson
...
```

---

## Examples

### Store a Tweet

```bash
curl -X POST http://localhost:8000/tweets \
  -H "Content-Type: application/json" \
  -d '{
    "id": "tweet-001",
    "text": "Just discovered an amazing #ML paper on transformers! @google @openai https://arxiv.org/abs/1234",
    "author_username": "mlresearcher",
    "hashtags": ["ML"],
    "mentions": ["google", "openai"],
    "urls": ["https://arxiv.org/abs/1234"]
  }'
```

### Search for Similar Content

```bash
curl -X POST http://localhost:8000/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "transformer neural networks research",
    "limit": 5
  }'
```

### Get Related Content

```bash
curl -X POST http://localhost:8000/related \
  -H "Content-Type: application/json" \
  -d '{
    "tweet_id": "tweet-001",
    "depth": 2
  }'
```

### Check Stats

```bash
curl http://localhost:8000/stats
```

**Response:**

```json
{
  "tweets": 1247,
  "users": 892,
  "hashtags": 341,
  "relationships": 5432,
  "embedding_provider": "deepseek",
  "embedding_model": "deepseek-embed"
}
```

---

## Troubleshooting

### Docker Compose Issues

**Ports already in use:**

```bash
# Check what's using ports
lsof -i :7474
lsof -i :7687
lsof -i :8000

# Change ports in docker-compose.yml
```

**Neo4j won't start:**

```bash
# Check logs
docker-compose logs neo4j

# Common fixes:
# - Increase memory: NEO4J_server_memory_heap_max__size=2G
# - Reset data: docker-compose down -v && docker-compose up -d
```

**API can't connect to Neo4j:**

```bash
# Wait for Neo4j to be healthy
docker-compose ps

# Should show "healthy" status for neo4j
# If not, check neo4j logs

# Verify API logs
docker-compose logs api
```

**Embeddings failing:**

```bash
# Check configuration
curl http://localhost:8000/config

# Verify API key
# Test provider directly:
curl https://api.openai.com/v1/embeddings \
  -H "Authorization: Bearer $EMBEDDING_API_KEY" \
  -d '{"input": "test", "model": "text-embedding-3-small"}'
```

**Playwright EPIPE error (Node.js compatibility):**

If you see `Error: write EPIPE` when running the bookmark fetcher:

```bash
# This is a Python 3.14 + Playwright Node.js 24 compatibility issue
# Solution 1: Use Python 3.11
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements-playwright.txt
playwright install chromium

# Solution 2: Run via Docker (uses Python 3.11)
docker build -t bookmark-fetcher ./bookmark-fetcher
docker run -v $(pwd)/cookies.json:/app/cookies.json bookmark-fetcher

# Solution 3: Pin Playwright to older version
pip install 'playwright>=1.40.0,<1.49.0'
playwright install chromium
```

### Kubernetes Issues

**Pod not starting:**

```bash
kubectl describe pod -n tweet-graph <pod-name>
kubectl logs -n tweet-graph <pod-name>

# Common issues:
# - Secret not created: kubectl get secrets -n tweet-graph
# - Image not found: Check image name and pull policy
# - Resource limits: Increase memory/CPU in deployment
```

**Secret issues:**

```bash
# Check secrets exist
kubectl get secrets -n tweet-graph

# Recreate secret
kubectl delete secret tweet-graph-secrets -n tweet-graph
kubectl create secret generic tweet-graph-secrets \
  --from-literal=EMBEDDING_API_KEY=your-key \
  -n tweet-graph

# Restart pods to pick up new secret
kubectl rollout restart deployment/tweet-graph-api -n tweet-graph
```

**Vector search not working:**

```bash
# Check vector index
curl http://localhost:8000/health

# Should show: "neo4j": true

# Check Neo4j logs
kubectl logs -n tweet-graph deployment/neo4j | grep -i vector

# Recreate index (API does this on startup)
kubectl rollout restart deployment/tweet-graph-api -n tweet-graph
```

---

## Development

### Local Development

```bash
# Start Neo4j only
docker run -p 7474:7474 -p 7687:7687 neo4j:5.15

# Run API locally
cd tweet-graph-api
pip install -r requirements.txt
python -m app.main

# Or with hot reload
pip install uvicorn
uvicorn app.main:app --reload
```

### Run Tests

```bash
cd tweet-graph-api
pip install pytest pytest-asyncio httpx
pytest tests/
```

### Build Images

```bash
# API
docker build -t tweet-graph-api:latest tweet-graph-api/

# Portal
docker build -t tweet-graph-portal:latest portal/

# Bookmark fetcher
docker build -t bookmark-fetcher:latest bookmark-fetcher/

# Push to registry
docker tag tweet-graph-api:latest your-registry/tweet-graph-api:latest
docker push your-registry/tweet-graph-api:latest

docker tag tweet-graph-portal:latest your-registry/tweet-graph-portal:latest
docker push your-registry/tweet-graph-portal:latest
```

---

## Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Code Style

- Python: Follow PEP 8
- Use type hints where possible
- Add docstrings for functions and classes
- Write tests for new features

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## Acknowledgments

- [Neo4j](https://neo4j.com/) - Graph database
- [FastAPI](https://fastapi.tiangolo.com/) - Modern Python web framework
- [OpenClaw](https://github.com/openclaw/openclaw) - Agent orchestration platform

---

## Support

- 📖 [Documentation](./docs/)
- 🐛 [Issue Tracker](https://github.com/yourusername/tweet-graph-system/issues)
- 💬 [Discussions](https://github.com/yourusername/tweet-graph-system/discussions)

---

**Made with ❤️ for the AI community**
