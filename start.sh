#!/bin/bash
# Tweet Graph System - Quick Start Script

set -e

echo "🐦 Tweet Graph System - Quick Start"
echo "====================================="

# Check for Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is required but not installed."
    exit 1
fi

if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo "❌ Docker Compose is required but not installed."
    exit 1
fi

# Check for .env file
if [ ! -f .env ]; then
    echo "📝 Creating .env from template..."
    cp .env.example .env
    echo ""
    echo "⚠️  Please edit .env and add your embedding provider API key:"
    echo "   vim .env"
    echo ""
    echo "   Then run this script again."
    exit 0
fi

# Detect docker compose command
if docker compose version &> /dev/null; then
    COMPOSE="docker compose"
else
    COMPOSE="docker-compose"
fi

echo ""
echo "📦 Starting services..."
$COMPOSE up -d

echo ""
echo "⏳ Waiting for Neo4j to be ready..."
until $COMPOSE exec neo4j wget --no-verbose --tries=1 --spider http://localhost:7474 2>/dev/null; do
    echo "   Still waiting..."
    sleep 2
done

echo ""
echo "✅ Services are up!"
echo ""
echo "📊 Services:"
echo "   • Neo4j Browser:  http://localhost:7474"
echo "   • Tweet Graph API: http://localhost:8000"
echo "   • API Docs:       http://localhost:8000/docs"
echo ""
echo "🔑 Neo4j Credentials:"
echo "   • Username: neo4j"
echo "   • Password: tweetgraph123"
echo ""
echo "📝 Quick Test:"
echo "   curl http://localhost:8000/health"
echo "   curl http://localhost:8000/stats"
echo ""
echo "To stop: $COMPOSE down"
