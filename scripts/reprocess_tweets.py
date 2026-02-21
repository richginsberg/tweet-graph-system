"""
Re-process existing tweets to fix embeddings and relationships
"""

import asyncio
import httpx

API_URL = "http://localhost:8000"

async def reprocess_tweets():
    """Re-store all tweets to fix embeddings and relationships"""
    
    # First, get all tweets from Neo4j
    from neo4j import AsyncGraphDatabase
    
    driver = AsyncGraphDatabase.driver(
        "bolt://localhost:7687",
        auth=("neo4j", "tweetgraph123")
    )
    
    tweets = []
    async with driver.session() as session:
        result = await session.run("""
            MATCH (t:Tweet)
            RETURN t.id as id, t.text as text, t.bookmark_url as bookmark_url
        """)
        tweets = [dict(record) async for record in result]
    
    await driver.close()
    
    print(f"Found {len(tweets)} tweets to reprocess")
    
    # Re-store each tweet via API (this will regenerate embeddings)
    async with httpx.AsyncClient() as client:
        for tweet in tweets:
            print(f"Reprocessing: {tweet['id']}")
            
            # Delete old tweet first
            async with driver.session() as session:
                await session.run("MATCH (t:Tweet {id: $id}) DETACH DELETE t", id=tweet["id"])
            
            # Re-store via API (generates new embedding)
            response = await client.post(
                f"{API_URL}/tweets",
                json={
                    "id": tweet["id"],
                    "text": tweet["text"],
                    "bookmark_url": tweet.get("bookmark_url")
                },
                timeout=30.0
            )
            
            if response.status_code == 200:
                print(f"  ✅ Fixed: {tweet['id'][:20]}...")
            else:
                print(f"  ❌ Failed: {response.text}")
    
    print("\nDone!")

if __name__ == "__main__":
    asyncio.run(reprocess_tweets())
