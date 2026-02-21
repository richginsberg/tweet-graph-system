"""
Fix truncated tweets using X/Twitter API v2

Usage:
    export TWITTER_BEARER_TOKEN=your_token
    python fix_truncated.py [--limit 10]
"""

import asyncio
import os
import argparse
from neo4j import AsyncGraphDatabase
from twitter_api import TwitterAPIClient

NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "tweetgraph123"

async def fix_truncated(limit: int = None):
    """Fix truncated tweets using X API v2"""
    
    bearer_token = os.environ.get("TWITTER_BEARER_TOKEN")
    if not bearer_token:
        print("ERROR: TWITTER_BEARER_TOKEN not set")
        print("\nTo get a bearer token:")
        print("1. Go to https://developer.twitter.com/en/portal/dashboard")
        print("2. Create a project/app")
        print("3. Get Bearer Token from Keys and Tokens tab")
        return
    
    twitter = TwitterAPIClient(bearer_token)
    driver = AsyncGraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    
    async with driver.session() as session:
        # Get truncated tweets
        query = "MATCH (t:Tweet) WHERE t.truncated = true RETURN t.id as id"
        if limit:
            query += f" LIMIT {limit}"
        
        result = await session.run(query)
        tweets = [dict(record) async for record in result]
        
        print(f"Found {len(tweets)} truncated tweets to fix")
        
        if not tweets:
            print("No truncated tweets found!")
            return
        
        # Process in batches of 100
        batch_size = 100
        total_fixed = 0
        
        for i in range(0, len(tweets), batch_size):
            batch = tweets[i:i+batch_size]
            tweet_ids = [t["id"] for t in batch]
            
            print(f"\nFetching batch {i//batch_size + 1}: {len(tweet_ids)} tweets...")
            
            # Fetch full data from API
            full_tweets = await twitter.get_tweets_batch(tweet_ids)
            
            print(f"Got {len(full_tweets)} tweets from API")
            
            # Update each tweet in Neo4j
            for tweet_data in full_tweets:
                await session.run("""
                    MATCH (t:Tweet {id: $id})
                    SET t.text = $text,
                        t.truncated = false,
                        t.author_username = $author
                """, id=tweet_data["id"], text=tweet_data["text"], 
                     author=tweet_data.get("author_username", ""))
                
                # Create hashtag relationships
                for tag in tweet_data.get("hashtags", []):
                    await session.run("""
                        MATCH (t:Tweet {id: $id})
                        MERGE (h:Hashtag {tag: $tag})
                        MERGE (t)-[:HAS_HASHTAG]->(h)
                    """, id=tweet_data["id"], tag=tag)
                
                # Create mention relationships
                for mention in tweet_data.get("mentions", []):
                    await session.run("""
                        MATCH (t:Tweet {id: $id})
                        MERGE (u:User {username: $mention})
                        MERGE (t)-[:MENTIONS]->(u)
                    """, id=tweet_data["id"], mention=mention)
                
                # Create URL relationships
                for url in tweet_data.get("urls", []):
                    await session.run("""
                        MATCH (t:Tweet {id: $id})
                        MERGE (u:URL {url: $url})
                        MERGE (t)-[:CONTAINS_URL]->(u)
                    """, id=tweet_data["id"], url=url)
                
                total_fixed += 1
                print(f"  Fixed: {tweet_data['id']} - {len(tweet_data['hashtags'])} hashtags, {len(tweet_data['mentions'])} mentions")
        
        # Count final relationships
        result = await session.run("""
            MATCH ()-[r]->() 
            RETURN type(r) as type, count(r) as count
            ORDER BY count DESC
        """)
        
        print(f"\n{'='*60}")
        print(f"Fixed {total_fixed} tweets")
        print(f"\nRelationships:")
        async for record in result:
            print(f"  {record['type']}: {record['count']}")
        print(f"{'='*60}")
    
    await driver.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fix truncated tweets using X API v2")
    parser.add_argument("--limit", type=int, help="Limit number of tweets to fix")
    args = parser.parse_args()
    
    asyncio.run(fix_truncated(args.limit))
