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
        "embedding_model": settings.get_embedding_config()["model"]
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
        result = await graph_service.store_tweet(tweet)
        
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
    """Bulk import bookmarks with deduplication"""
    new_count = 0
    duplicate_count = 0
    
    for tweet_data in request.bookmarks:
        tweet = TweetCreate(**tweet_data)
        existing = await graph_service.get_tweet(tweet.id)
        
        if not existing:
            await graph_service.store_tweet(tweet)
            new_count += 1
        else:
            duplicate_count += 1
    
    return {
        "total_received": len(request.bookmarks),
        "new_stored": new_count,
        "duplicates_skipped": duplicate_count
    }

@app.get("/stats")
async def get_stats():
    """Get database statistics"""
    stats = await graph_service.get_stats()
    stats["embedding_provider"] = settings.EMBEDDING_PROVIDER
    stats["embedding_model"] = settings.get_embedding_config()["model"]
    return stats

@app.get("/config")
async def get_config():
    """Get current embedding configuration"""
    config = settings.get_embedding_config()
    # Don't expose API key
    config["api_key"] = "***" if config.get("api_key") else None
    return config

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
