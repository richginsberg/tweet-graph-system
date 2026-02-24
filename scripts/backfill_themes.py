#!/usr/bin/env python3
"""
Backfill themes and entities for existing tweets

This script:
1. Fetches all tweets without themes
2. Extracts themes and entities using keyword matching
3. Updates Neo4j with theme/entity relationships

Usage:
    python backfill_themes.py [--limit 100] [--dry-run]
"""

import asyncio
import argparse
import httpx
import re
from typing import List, Set, Tuple

API_URL = "http://localhost:8000"

# Theme keywords - expand as needed
THEME_KEYWORDS = {
    "ai": ["ai", "artificial intelligence", "machine learning", "ml", "deep learning", "neural network"],
    "llm": ["llm", "gpt", "chatgpt", "claude", "openai", "anthropic", "gemini", "llama", "mistral", "deepseek", "qwen"],
    "agents": ["agent", "agentic", "autonomous", "automation", "workflow", "rag", "langchain"],
    "infrastructure": ["cloud", "aws", "gcp", "azure", "kubernetes", "docker", "api", "serverless", "terraform"],
    "business": ["startup", "b2b", "b2c", "saas", "enterprise", "founder", "vc", "funding", "revenue", "mrr"],
    "crypto": ["blockchain", "crypto", "bitcoin", "ethereum", "defi", "nft", "web3", "solana"],
    "dev": ["python", "javascript", "typescript", "rust", "go", "coding", "programming", "github", "git"],
    "security": ["security", "privacy", "encryption", "auth", "authentication", "cyber"],
    "hardware": ["gpu", "cpu", "nvidia", "amd", "h100", "chip", "semiconductor", "hardware"],
    "data": ["data", "analytics", "visualization", "database", "sql", "nosql", "vector"],
    "mobile": ["ios", "android", "mobile", "app", "swift", "kotlin"],
    "design": ["design", "ui", "ux", "figma", "interface", "skeuomorphic"],
}


def extract_themes_and_entities(text: str) -> Tuple[List[str], List[str]]:
    """Extract themes and proper nouns from tweet text"""
    if not text:
        return [], []
    
    text_lower = text.lower()
    
    # Find matching themes
    themes = set()
    for theme_category, keywords in THEME_KEYWORDS.items():
        for keyword in keywords:
            if keyword in text_lower:
                themes.add(theme_category)
                break
    
    # Extract proper nouns - be more conservative
    entities = set()
    
    # Multi-word proper nouns (e.g., "Elon Musk", "Sam Altman")
    multi_word = re.findall(r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\b', text)
    entities.update(multi_word)
    
    # Skip common words that get mistakenly capitalized
    skip_words = {
        'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by',
        'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had', 'do', 'does', 
        'did', 'will', 'would', 'could', 'should', 'may', 'might', 'must', 'this', 'that', 
        'these', 'those', 'it', 'its', 'use', 'using', 'used', 'ask', 'give', 'can', 'just',
        'here', 'there', 'where', 'when', 'what', 'which', 'who', 'how', 'why', 'get', 'got',
        'if', 'then', 'else', 'also', 'even', 'still', 'already', 'yet', 'now', 'new', 'docs',
        'integration', 'memory', 'introducing', 'everything', 'heres', 'here\'s', 'lets', 
        'let\'s', 'you', 'your', 'yours', 'we', 'us', 'our', 'ours', 'they', 'them', 'their',
        'all', 'some', 'any', 'each', 'every', 'both', 'few', 'many', 'most', 'other', 'another',
        'such', 'own', 'same', 'so', 'than', 'too', 'very', 'just', 'only', 'code', 'example',
        'thread', 'tweet', 'post', 'link', 'video', 'image', 'check', 'try', 'run', 'make',
        'first', 'second', 'third', 'last', 'next', 'best', 'better', 'good', 'great', 'free',
        'full', 'open', 'build', 'built', 'building', 'create', 'created', 'creating', 'start',
        'started', 'starting', 'read', 'reading', 'write', 'writing', 'written', 'learn',
        'learning', 'learned', 'work', 'working', 'worked', 'today', 'yesterday', 'tomorrow',
        'week', 'month', 'year', 'day', 'hour', 'minute', 'second', 'time', 'number', 'one',
        'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine', 'ten'
    }
    
    # Single proper nouns - only if they look like names/companies
    sentences = re.split(r'[.!?]+\s*', text)
    for i, sentence in enumerate(sentences):
        # Skip empty or very short sentences
        if len(sentence.strip()) < 5:
            continue
            
        words = sentence.split()
        for j, word in enumerate(words):
            # Skip first word of first sentence
            if i == 0 and j == 0:
                continue
            
            # Clean the word
            clean = re.sub(r'[^a-zA-Z]', '', word)
            
            # Skip short words, common words, and all-caps acronyms
            if len(clean) < 3:
                continue
            if clean.lower() in skip_words:
                continue
            if clean.isupper():
                continue
            if not clean[0].isupper():
                continue
                
            # Only add if it looks like a proper noun (has capital + lowercase)
            if clean[0].isupper() and clean[1:].islower():
                entities.add(clean)
    
    return list(themes), list(entities)


async def fetch_all_tweets() -> List[dict]:
    """Fetch all tweets using pagination"""
    async with httpx.AsyncClient() as client:
        all_tweets = []
        offset = 0
        limit = 100
        
        while True:
            response = await client.get(
                f"{API_URL}/tweets", 
                params={"limit": limit, "offset": offset},
                timeout=60.0
            )
            if response.status_code != 200:
                raise Exception(f"Failed to fetch tweets: {response.text}")
            
            data = response.json()
            tweets = data.get("tweets", [])
            all_tweets.extend(tweets)
            
            if not data.get("has_more", False):
                break
            
            offset += limit
            print(f"Fetched {len(all_tweets)} tweets so far...")
        
        return all_tweets


async def update_tweet_themes(tweet_id: str, themes: List[str], entities: List[str]):
    """Update tweet with theme and entity relationships via Neo4j"""
    from neo4j import AsyncGraphDatabase
    
    # Connect directly to Neo4j
    driver = AsyncGraphDatabase.driver("bolt://localhost:7687", auth=("neo4j", "tweetgraph123"))
    
    async with driver.session() as session:
        # Add theme relationships
        for theme in themes:
            await session.run("""
                MATCH (t:Tweet {id: $id})
                MERGE (th:Theme {name: $theme})
                MERGE (t)-[:ABOUT_THEME]->(th)
            """, id=tweet_id, theme=theme)
        
        # Add entity relationships
        for entity in entities:
            await session.run("""
                MATCH (t:Tweet {id: $id})
                MERGE (e:Entity {name: $name})
                SET e.type = 'proper_noun'
                MERGE (t)-[:MENTIONS_ENTITY]->(e)
            """, id=tweet_id, name=entity)
    
    await driver.close()


async def main():
    parser = argparse.ArgumentParser(description="Backfill themes and entities for tweets")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of tweets to process")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done without making changes")
    args = parser.parse_args()
    
    print("=" * 60)
    print("THEME & ENTITY BACKFILL")
    print("=" * 60)
    
    # Fetch tweets
    print("\nFetching tweets...")
    tweets = await fetch_all_tweets()
    
    if args.limit:
        tweets = tweets[:args.limit]
    
    print(f"Found {len(tweets)} tweets to process")
    
    if args.dry_run:
        print("\n[DRY RUN - no changes will be made]")
    
    # Stats
    total_themes = 0
    total_entities = 0
    processed = 0
    
    for tweet in tweets:
        tweet_id = tweet.get("id")
        text = tweet.get("text", "")
        
        if not text:
            continue
        
        # Extract themes and entities
        themes, entities = extract_themes_and_entities(text)
        
        if themes or entities:
            if args.dry_run:
                print(f"\nTweet {tweet_id}:")
                print(f"  Text: {text[:100]}...")
                print(f"  Themes: {themes}")
                print(f"  Entities: {entities[:5]}...")
            else:
                await update_tweet_themes(tweet_id, themes, entities)
            
            total_themes += len(themes)
            total_entities += len(entities)
        
        processed += 1
        if processed % 50 == 0:
            print(f"Processed {processed}/{len(tweets)} tweets...")
    
    print("\n" + "=" * 60)
    print("BACKFILL COMPLETE")
    print("=" * 60)
    print(f"Tweets processed: {processed}")
    print(f"Themes extracted: {total_themes}")
    print(f"Entities extracted: {total_entities}")
    
    if not args.dry_run:
        # Fetch updated stats
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{API_URL}/stats")
            if response.status_code == 200:
                stats = response.json()
                print(f"\nDatabase stats:")
                print(f"  Tweets: {stats.get('tweets', 0)}")
                print(f"  Users: {stats.get('users', 0)}")
                print(f"  Relationships: {stats.get('relationships', 0)}")


if __name__ == "__main__":
    asyncio.run(main())
