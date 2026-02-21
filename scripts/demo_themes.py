"""
Quick test: themes and entities extraction with demo tweets
"""

import asyncio
from neo4j import AsyncGraphDatabase
from theme_extraction import extract_themes_and_entities

NEO4J_URI = "bolt://localhost:7687"
NEO4J_AUTH = ("neo4j", "tweetgraph123")

# Demo tweets with rich content
demo_tweets = [
    {
        "id": "demo-001",
        "text": "OpenAI just released GPT-5 with amazing reasoning capabilities. Claude from Anthropic is still my favorite for coding. #AI #ML",
        "author": "aitoday",
        "truncated": False
    },
    {
        "id": "demo-002", 
        "text": "Elon Musk announced Tesla will use Neural Networks for Full Self Driving. Venture Capital firms like Andreessen Horowitz betting big on autonomy.",
        "author": "techwatch",
        "truncated": False
    },
    {
        "id": "demo-003",
        "text": "AWS vs Google Cloud vs Azure cost comparison. DeepSeek running on Kubernetes cluster with GPU acceleration. B2B SaaS startups migrating to cloud.",
        "author": "cloudguru",
        "truncated": False
    },
    {
        "id": "demo-004",
        "text": "Bitcoin and Ethereum mining under pressure. DeFi protocols on Arbitrum seeing growth. Web3 projects need better UX. Vitalik Buterin proposing new standards.",
        "author": "cryptodaily",
        "truncated": False
    },
    {
        "id": "demo-005",
        "text": "Python 4.0 announced with JIT compiler. Rust gaining popularity for systems programming. TypeScript becoming standard for frontend dev. GitHub Copilot changing workflows.",
        "author": "devweekly",
        "truncated": False
    }
]

async def store_with_themes():
    driver = AsyncGraphDatabase.driver(NEO4J_URI, auth=NEO4J_AUTH)
    
    async with driver.session() as session:
        # Clear old tweets
        await session.run("MATCH (t:Tweet) DETACH DELETE t")
        print("Cleared old tweets\n")
        
        for tweet in demo_tweets:
            # Extract themes and entities
            themes, entities = extract_themes_and_entities(tweet["text"])
            
            print(f"Processing: {tweet['id']}")
            print(f"  Text: {tweet['text'][:80]}...")
            print(f"  Themes: {themes}")
            print(f"  Entities: {entities}")
            print()
            
            # Store tweet
            await session.run("""
                MERGE (t:Tweet {id: $id})
                SET t.text = $text,
                    t.author_username = $author,
                    t.truncated = $truncated
            """, id=tweet["id"], text=tweet["text"], 
                 author=tweet["author"], truncated=tweet["truncated"])
            
            # Store author
            await session.run("""
                MATCH (t:Tweet {id: $id})
                MERGE (u:User {username: $author})
                MERGE (u)-[:POSTED]->(t)
            """, id=tweet["id"], author=tweet["author"])
            
            # Store themes
            for theme in themes:
                await session.run("""
                    MATCH (t:Tweet {id: $id})
                    MERGE (th:Theme {name: $theme})
                    MERGE (t)-[:ABOUT_THEME]->(th)
                """, id=tweet["id"], theme=theme)
            
            # Store entities
            for entity in entities:
                await session.run("""
                    MATCH (t:Tweet {id: $id})
                    MERGE (e:Entity {name: $entity})
                    MERGE (t)-[:MENTIONS_ENTITY]->(e)
                """, id=tweet["id"], entity=entity)
        
        # Get stats
        print("\n" + "="*60)
        print("DATABASE STATS")
        print("="*60)
        
        tweets = await session.run("MATCH (t:Tweet) RETURN count(t) as c")
        print(f"Tweets: {(await tweets.single())['c']}")
        
        themes = await session.run("MATCH (th:Theme) RETURN count(th) as c")
        print(f"Themes: {(await themes.single())['c']}")
        
        entities = await session.run("MATCH (e:Entity) RETURN count(e) as c")
        print(f"Entities: {(await entities.single())['c']}")
        
        rels = await session.run("MATCH ()-[r]->() RETURN type(r) as t, count(r) as c")
        print("\nRelationships:")
        async for record in rels:
            print(f"  {record['t']}: {record['c']}")
        
        print("="*60)
    
    await driver.close()

if __name__ == "__main__":
    asyncio.run(store_with_themes())
