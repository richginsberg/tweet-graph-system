#!/bin/bash
# Tweet Graph System - Stop Script

# Detect docker compose command
if docker compose version &> /dev/null; then
    COMPOSE="docker compose"
else
    COMPOSE="docker-compose"
fi

echo "🛑 Stopping Tweet Graph System..."
$COMPOSE down

echo ""
echo "✅ Services stopped."
echo ""
echo "To remove data volumes: $COMPOSE down -v"
