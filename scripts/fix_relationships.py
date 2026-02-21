"""
Fix relationships for existing tweets - improved extraction
"""

import asyncio
import re
from neo4j import AsyncGraphDatabase

async def fix_relationships():
    driver = AsyncGraphDatabase.driver(
        "bolt://localhost:7687",
        auth=("neo4j", "tweetgraph123")
    )
    
    async with driver.session() as session:
        # Get all tweets
        result = await session.run("""
            MATCH (t:Tweet)
            WHERE t.text IS NOT NULL
            RETURN t.id as id, t.text as text
        """)
        
        tweets = [dict(record) async for record in result]
        print(f"Found {len(tweets)} tweets to process\n")
        
        fixed_count = 0
        total_hashtags = 0
        total_mentions = 0
        total_urls = 0
        
        for tweet in tweets:
            tweet_id = tweet["id"]
            text = tweet.get("text", "")
            
            if not text:
                continue
            
            # Clean text - replace newlines with spaces for better matching
            text_clean = ' '.join(text.split())
            
            # Extract hashtags - more lenient pattern
            hashtags = list(set(re.findall(r'#(\w+)', text)))
            
            # Extract mentions - more lenient pattern  
            mentions = list(set(re.findall(r'@(\w+)', text)))
            
            # Extract URLs - handle broken URLs with newlines
            # First try standard URLs
            urls = list(set(re.findall(r'https?://[^\s<>"]+', text_clean)))
            
            # Also look for http/https that might be broken
            if 'http' in text.lower() and not urls:
                # Try to reconstruct broken URLs
                http_match = re.search(r'https?[:/\\]+[^\s]*', text, re.IGNORECASE)
                if http_match:
                    urls.append(http_match.group().replace('\n', ''))
            
            print(f"Tweet {tweet_id}:")
            print(f"  Text: {text[:100]}...")
            
            # Create hashtag relationships
            for tag in hashtags:
                await session.run("""
                    MATCH (t:Tweet {id: $id})
                    MERGE (h:Hashtag {tag: $tag})
                    MERGE (t)-[:HAS_HASHTAG]->(h)
                """, id=tweet_id, tag=tag)
                total_hashtags += 1
            
            # Create mention relationships
            for mention in mentions:
                await session.run("""
                    MATCH (t:Tweet {id: $id})
                    MERGE (u:User {username: $mention})
                    MERGE (t)-[:MENTIONS]->(u)
                """, id=tweet_id, mention=mention)
                total_mentions += 1
            
            # Create URL relationships
            for url in urls[:5]:  # Limit to 5 URLs per tweet
                await session.run("""
                    MATCH (t:Tweet {id: $id})
                    MERGE (u:URL {url: $url})
                    MERGE (t)-[:CONTAINS_URL]->(u)
                """, id=tweet_id, url=url)
                total_urls += 1
            
            print(f"  Hashtags: {hashtags}")
            print(f"  Mentions: {mentions}")
            print(f"  URLs: {urls[:5]}")
            print()
            
            if hashtags or mentions or urls:
                fixed_count += 1
        
        # Count all relationships
        result = await session.run("MATCH ()-[r]->() RETURN count(r) as count")
        rel_count = (await result.single())["count"]
        
        # Count by type
        result = await session.run("""
            MATCH ()-[r]->()
            RETURN type(r) as type, count(r) as count
            ORDER BY count DESC
        """)
        rel_types = {}
        async for record in result:
            rel_types[record["type"]] = record["count"]
        
        print(f"{'='*60}")
        print(f"SUMMARY")
        print(f"{'='*60}")
        print(f"Tweets processed: {len(tweets)}")
        print(f"Tweets with entities: {fixed_count}")
        print(f"Hashtags found: {total_hashtags}")
        print(f"Mentions found: {total_mentions}")
        print(f"URLs found: {total_urls}")
        print(f"\nTotal relationships: {rel_count}")
        print(f"By type: {rel_types}")
        print(f"{'='*60}")
    
    await driver.close()

if __name__ == "__main__":
    asyncio.run(fix_relationships())
