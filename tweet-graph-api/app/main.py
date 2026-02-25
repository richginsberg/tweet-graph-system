# Tweet Graph API

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

from app.config import settings
from app.neo4j_client import Neo4jClient
from app.graph_service import GraphService
from app.models import (
    TweetCreate, TweetResponse, SearchRequest, SearchResponse,
    RelatedRequest, RelatedResponse, BookmarkSyncRequest
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

neo4j_client = None
graph_service = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global neo4j_client, graph_service
    logger.info("Starting Tweet Graph API...")
    
    # Log embedding configuration
    embedding_config = settings.get_embedding_config()
    logger.info(f"Embedding Provider: {settings.EMBEDDING_PROVIDER}")
    logger.info(f"Embedding Model: {embedding_config['model']}")
    logger.info(f"Embedding Dimensions: {embedding_config['dimensions']}")
    
    neo4j_client = Neo4jClient(
        uri=settings.NEO4J_URI,
        user=settings.NEO4J_USER,
        password=settings.NEO4J_PASSWORD
    )
    await neo4j_client.connect()
    
    graph_service = GraphService(neo4j_client, embedding_config)
    await graph_service.init_vector_index()
    
    logger.info("Connected to Neo4j and initialized indexes")
    
    yield
    
    logger.info("Shutting down Tweet Graph API...")
    await neo4j_client.close()

app = FastAPI(
    title="Tweet Graph API",
    description="Store and retrieve tweets in Neo4j graph database",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "neo4j": neo4j_client.connected,
        "embedding_provider": settings.EMBEDDING_PROVIDER,
        "embedding_model": settings.get_embedding_config()["model"],
        "twitter_api_tier": settings.TWITTER_API_TIER,
        "enrichment_enabled": settings.TWITTER_API_TIER in ("basic", "pro")
    }

@app.post("/tweets", response_model=TweetResponse)
async def store_tweet(tweet: TweetCreate):
    """Store a tweet in the graph database"""
    try:
        # Check for duplicates
        existing = await graph_service.get_tweet(tweet.id)
        if existing:
            return TweetResponse(
                id=tweet.id,
                text=existing["text"],
                stored=False,
                message="Tweet already exists"
            )
        
        # Store tweet with embeddings
        result = await graph_service.store_tweet(tweet, tweet.truncated)
        
        return TweetResponse(
            id=tweet.id,
            text=tweet.text,
            stored=True,
            message="Tweet stored successfully",
            related_count=result.get("relationships_created", 0)
        )
    except Exception as e:
        logger.error(f"Error storing tweet: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/tweets/all")
async def get_all_tweets():
    """Get all tweets (legacy - use /tweets for paginated)"""
    return await graph_service.get_all_tweets()

@app.get("/tweets")
async def get_tweets_paginated(limit: int = 50, offset: int = 0):
    """Get paginated tweets for lazy loading"""
    return await graph_service.get_tweets_paginated(limit, offset)

@app.get("/tweets/truncated")
async def get_truncated_tweets():
    """Get all truncated tweets that need enrichment"""
    return await graph_service.get_truncated_tweets()

@app.post("/tweets/{tweet_id}/enrich")
async def enrich_tweet(tweet_id: str):
    """Enrich a truncated tweet via X API v2"""
    result = await graph_service.enrich_tweet_via_api(tweet_id, settings.TWITTER_BEARER_TOKEN)
    if result is None:
        raise HTTPException(status_code=400, detail="Tweet not found or already enriched")
    if result.get("error"):
        raise HTTPException(status_code=500, detail=result["error"])
    return result

@app.post("/tweets/enrich-all")
async def enrich_all_truncated():
    """Enrich all truncated tweets via X API v2 (batch)"""
    result = await graph_service.enrich_all_truncated(settings.TWITTER_BEARER_TOKEN)
    return result

@app.get("/tweets/{tweet_id}")
async def get_tweet(tweet_id: str):
    """Get a tweet by ID"""
    tweet = await graph_service.get_tweet(tweet_id)
    if not tweet:
        raise HTTPException(status_code=404, detail="Tweet not found")
    return tweet

@app.post("/search", response_model=SearchResponse)
async def search_tweets(request: SearchRequest):
    """Vector similarity search for tweets"""
    results = await graph_service.vector_search(request.query, request.limit)
    return SearchResponse(
        query=request.query,
        results=results,
        count=len(results)
    )

@app.post("/related", response_model=RelatedResponse)
async def get_related(request: RelatedRequest):
    """Get related nodes via graph traversal"""
    results = await graph_service.get_related(
        request.tweet_id,
        request.depth,
        request.relationship_types
    )
    return RelatedResponse(
        tweet_id=request.tweet_id,
        related=results,
        count=len(results)
    )

@app.post("/bookmarks/sync")
async def sync_bookmarks(request: BookmarkSyncRequest):
    """Bulk import bookmarks with auto-enrichment for truncated tweets"""
    import os
    from app.twitter_api import TwitterAPIClient
    
    new_count = 0
    duplicate_count = 0
    updated_count = 0
    enriched_count = 0
    
    # Check if X API token is available for enrichment
    twitter_token = os.environ.get("TWITTER_BEARER_TOKEN")
    twitter_client = TwitterAPIClient(twitter_token) if twitter_token else None
    
    for tweet_data in request.bookmarks:
        tweet = TweetCreate(**tweet_data)
        existing = await graph_service.get_tweet(tweet.id)
        
        if not existing:
            # New tweet - try to enrich if truncated
            if tweet.truncated and twitter_client:
                full_data = await twitter_client.get_tweet(tweet.id)
                if full_data:
                    tweet.text = full_data.get("text", tweet.text)
                    tweet.truncated = False
                    tweet.hashtags = full_data.get("hashtags", tweet.hashtags)
                    tweet.mentions = full_data.get("mentions", tweet.mentions)
                    tweet.author_username = full_data.get("author_username", tweet.author_username)
                    enriched_count += 1
            
            await graph_service.store_tweet(tweet)
            new_count += 1
        else:
            # Duplicate - check if we should update
            existing_truncated = existing.get("truncated", True)
            incoming_truncated = tweet.truncated if tweet.truncated is not None else True
            
            # Update if: existing is truncated AND (incoming is not truncated OR we can enrich via API)
            should_update = False
            
            if existing_truncated and not incoming_truncated:
                # Incoming has full text, use it
                should_update = True
                await graph_service.update_tweet_full_text(
                    tweet.id, 
                    tweet.text,
                    tweet.hashtags or [],
                    tweet.mentions or [],
                    tweet.author_username
                )
                updated_count += 1
            elif existing_truncated and twitter_client:
                # Try to enrich via X API
                full_data = await twitter_client.get_tweet(tweet.id)
                if full_data and full_data.get("text"):
                    await graph_service.update_tweet_full_text(
                        tweet.id, 
                        full_data["text"],
                        full_data.get("hashtags", []),
                        full_data.get("mentions", []),
                        full_data.get("author_username")
                    )
                    enriched_count += 1
                    updated_count += 1
            elif tweet.author_username and not existing.get("author"):
                # Just update author if missing
                await graph_service.update_tweet_author(tweet.id, tweet.author_username)
                updated_count += 1
            
            duplicate_count += 1
    
    return {
        "total_received": len(request.bookmarks),
        "new_stored": new_count,
        "duplicates_skipped": duplicate_count,
        "updated": updated_count,
        "enriched": enriched_count
    }

@app.get("/stats")
async def get_stats():
    """Get database statistics"""
    stats = await graph_service.get_stats()
    stats["embedding_provider"] = settings.EMBEDDING_PROVIDER
    stats["embedding_model"] = settings.get_embedding_config()["model"]
    return stats

@app.get("/graph")
async def get_graph():
    """Get graph data for visualization (nodes and links)"""
    return await graph_service.get_graph_data()

@app.get("/themes")
async def get_themes():
    """Get all themes with tweet counts"""
    return await graph_service.get_themes()

@app.get("/entities")
async def get_entities():
    """Get all entities with mention counts"""
    return await graph_service.get_entities()

@app.get("/config")
async def get_config():
    """Get current embedding configuration"""
    config = settings.get_embedding_config()
    # Don't expose API key
    config["api_key"] = "***" if config.get("api_key") else None
    return config

@app.delete("/tweets/all")
async def clear_all_tweets():
    """Clear all tweets from the database (keeps other nodes)"""
    result = await graph_service.clear_all_tweets()
    return {
        "message": "All tweets cleared",
        "deleted": result.get("deleted", 0)
    }

@app.delete("/database/all")
async def clear_database():
    """Clear ALL data from the database - use with caution"""
    result = await graph_service.clear_database()
    return {
        "message": "Database cleared",
        "deleted_nodes": result.get("deleted_nodes", 0),
        "deleted_relationships": result.get("deleted_relationships", 0)
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
