"""
Complete bookmark pipeline:
1. Clear old bookmarks
2. Fetch batch from browser (truncated)
3. Use X API v2 to get full data
4. Extract themes and proper nouns
5. Store with relationships
"""

import asyncio
import json
import logging
import re
from datetime import datetime, timezone
from typing import List, Dict, Set
import httpx
from playwright.async_api import async_playwright
from neo4j import AsyncGraphDatabase

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configuration
TWEET_GRAPH_API_URL = "http://localhost:8000"
BOOKMARKS_URL = "https://x.com/i/bookmarks"
COOKIES_FILE = "cookies.json"
BATCH_SIZE = 20
TWITTER_BEARER_TOKEN = None  # Set via env var

# Neo4j
NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "tweetgraph123"

class BookmarkPipeline:
    def __init__(self, bearer_token: str = None):
        self.bearer_token = bearer_token
        self.cookies = self.load_cookies()
        self.driver = AsyncGraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    
    def load_cookies(self) -> List[Dict]:
        try:
            with open(COOKIES_FILE, "r") as f:
                return json.load(f)
        except:
            logger.warning("No cookies file")
            return []
    
    async def clear_old_tweets(self):
        """Clear all existing tweets"""
        async with self.driver.session() as session:
            result = await session.run("MATCH (t:Tweet) DETACH DELETE t RETURN count(t) as deleted")
            deleted = (await result.single())["deleted"]
            logger.info(f"Cleared {deleted} old tweets")
    
    async def fetch_browser_batch(self) -> List[Dict]:
        """Fetch batch of bookmarks from browser (truncated)"""
        logger.info(f"Fetching {BATCH_SIZE} bookmarks from browser...")
        
        bookmarks = []
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            
            if self.cookies:
                formatted = [{"name": c.get("name", ""), "value": c.get("value", ""),
                             "domain": c.get("domain", ".x.com"), "path": c.get("path", "/")} 
                            for c in self.cookies]
                await context.add_cookies(formatted)
                logger.info(f"Loaded {len(formatted)} cookies")
            
            page = await context.new_page()
            await page.goto(BOOKMARKS_URL, wait_until="networkidle")
            await page.wait_for_selector('[data-testid="tweet"]', timeout=30000)
            
            # Scroll a bit
            for _ in range(3):
                await page.evaluate("window.scrollBy(0, 1000)")
                await asyncio.sleep(1)
            
            tweets = await page.query_selector_all('[data-testid="tweet"]')
            logger.info(f"Found {len(tweets)} tweets on page")
            
            for tweet_elem in tweets[:BATCH_SIZE]:
                try:
                    data = await self.parse_tweet(tweet_elem)
                    if data.get("id"):
                        bookmarks.append(data)
                except Exception as e:
                    logger.debug(f"Parse error: {e}")
            
            await browser.close()
        
        logger.info(f"Fetched {len(bookmarks)} bookmarks from browser")
        return bookmarks
    
    async def parse_tweet(self, elem) -> Dict:
        """Parse tweet from browser (truncated)"""
        link = await elem.query_selector('a[href*="/status/"]')
        if not link:
            return {}
        href = await link.get_attribute("href")
        tweet_id = href.split("/status/")[-1].split("?")[0]
        
        text_elem = await elem.query_selector('[data-testid="tweetText"]')
        text = await text_elem.inner_text() if text_elem else ""
        
        author_elem = await elem.query_selector('[data-testid="User-Name"]')
        author = await author_elem.inner_text() if author_elem else ""
        author_username = author.split("@")[-1].split("\n")[0] if author else ""
        
        return {
            "id": tweet_id,
            "text": text,
            "author_username": author_username,
            "bookmark_url": f"https://x.com{href}",
            "truncated": True  # Browser fetches are always truncated
        }
    
    async def enrich_with_api(self, bookmarks: List[Dict]) -> List[Dict]:
        """Use X API v2 to get full tweet data"""
        if not self.bearer_token:
            logger.warning("No bearer token - skipping API enrichment")
            return bookmarks
        
        logger.info(f"Enriching {len(bookmarks)} tweets via API v2...")
        
        tweet_ids = [b["id"] for b in bookmarks]
        url = "https://api.twitter.com/2/tweets"
        
        params = {
            "ids": ",".join(tweet_ids[:100]),
            "tweet.fields": "created_at,author_id,entities,public_metrics",
            "expansions": "author_id",
            "user.fields": "username,name"
        }
        
        headers = {"Authorization": f"Bearer {self.bearer_token}"}
        
        enriched = []
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params, headers=headers, timeout=30.0)
            
            if response.status_code == 200:
                data = response.json()
                
                # Build author lookup
                authors = {}
                if "includes" in data and "users" in data["includes"]:
                    for user in data["includes"]["users"]:
                        authors[user["id"]] = user.get("username", "")
                
                # Parse enriched tweets
                for tweet in data.get("data", []):
                    entities = tweet.get("entities", {})
                    
                    # Get full text
                    full_text = tweet.get("text", "")
                    
                    # Extract entities
                    hashtags = [h["tag"] for h in entities.get("hashtags", [])]
                    mentions = [m["username"] for m in entities.get("mentions", [])]
                    urls = [u.get("expanded_url", u.get("url", "")) 
                            for u in entities.get("urls", [])]
                    
                    # Extract themes and proper nouns
                    themes, proper_nouns = self.extract_themes_and_entities(full_text)
                    
                    author_id = tweet.get("author_id")
                    
                    enriched.append({
                        "id": tweet["id"],
                        "text": full_text,
                        "author_username": authors.get(author_id, ""),
                        "hashtags": hashtags,
                        "mentions": mentions,
                        "urls": urls[:5],
                        "themes": themes,
                        "proper_nouns": proper_nouns,
                        "created_at": tweet.get("created_at"),
                        "truncated": False  # API returns full text
                    })
                
                logger.info(f"Enriched {len(enriched)} tweets via API")
            else:
                logger.error(f"API error: {response.status_code}")
                return bookmarks
        
        return enriched if enriched else bookmarks
    
    def extract_themes_and_entities(self, text: str) -> tuple:
        """Extract themes and proper nouns from text"""
        themes = set()
        proper_nouns = set()
        
        # Common AI/tech themes
        theme_keywords = {
            "ai", "artificial intelligence", "machine learning", "ml", "deep learning",
            "neural network", "llm", "gpt", "chatgpt", "claude", "openai", "anthropic",
            "automation", "agent", "agentic", "robotics", "autonomous",
            "blockchain", "crypto", "bitcoin", "ethereum", "defi", "nft",
            "startup", "saas", "b2b", "b2c", "enterprise", "founder", "vc", "funding",
            "api", "sdk", "infrastructure", "cloud", "aws", "gcp", "azure",
            "security", "privacy", "encryption", "authentication",
            "data", "analytics", "visualization", "dashboard", "metrics",
            "mobile", "ios", "android", "web", "frontend", "backend", "fullstack",
            "devops", "kubernetes", "docker", "ci/cd", "monitoring",
            "python", "javascript", "typescript", "rust", "go", "java", "c++"
        }
        
        text_lower = text.lower()
        text_words = set(re.findall(r'\b\w+\b', text_lower))
        
        # Find themes
        for keyword in theme_keywords:
            if keyword in text_lower:
                themes.add(keyword)
        
        # Extract proper nouns (capitalized words not at sentence start)
        # Look for patterns like "OpenAI", "Elon Musk", "New York"
        sentences = text.split('. ')
        for i, sentence in enumerate(sentences):
            words = sentence.split()
            for j, word in enumerate(words):
                # Skip first word of sentence (usually capitalized)
                if i == 0 and j == 0:
                    continue
                
                # Check if it's a proper noun (starts with capital, contains lowercase)
                if word and word[0].isupper() and any(c.islower() for c in word[1:]):
                    # Clean the word
                    clean = re.sub(r'[^a-zA-Z]', '', word)
                    if len(clean) > 2:  # Ignore short words
                        proper_nouns.add(clean)
        
        # Also extract multi-word proper nouns
        proper_noun_patterns = re.findall(r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\b', text)
        for pn in proper_noun_patterns:
            proper_nouns.add(pn)
        
        return list(themes), list(proper_nouns)
    
    async def store_with_relationships(self, bookmarks: List[Dict]):
        """Store tweets with all relationships including themes and proper nouns"""
        logger.info(f"Storing {len(bookmarks)} tweets with relationships...")
        
        async with self.driver.session() as session:
            for tweet in bookmarks:
                # Store tweet
                await session.run("""
                    MERGE (t:Tweet {id: $id})
                    SET t.text = $text,
                        t.author_username = $author,
                        t.truncated = $truncated,
                        t.created_at = $created_at,
                        t.bookmark_url = $bookmark_url
                """, 
                    id=tweet["id"],
                    text=tweet["text"],
                    author=tweet.get("author_username", ""),
                    truncated=tweet.get("truncated", True),
                    created_at=tweet.get("created_at"),
                    bookmark_url=tweet.get("bookmark_url", "")
                )
                
                # Create author relationship
                if tweet.get("author_username"):
                    await session.run("""
                        MATCH (t:Tweet {id: $id})
                        MERGE (u:User {username: $author})
                        MERGE (u)-[:POSTED]->(t)
                    """, id=tweet["id"], author=tweet["author_username"])
                
                # Create hashtag relationships
                for tag in tweet.get("hashtags", []):
                    await session.run("""
                        MATCH (t:Tweet {id: $id})
                        MERGE (h:Hashtag {tag: $tag})
                        MERGE (t)-[:HAS_HASHTAG]->(h)
                    """, id=tweet["id"], tag=tag)
                
                # Create mention relationships
                for mention in tweet.get("mentions", []):
                    await session.run("""
                        MATCH (t:Tweet {id: $id})
                        MERGE (u:User {username: $mention})
                        MERGE (t)-[:MENTIONS]->(u)
                    """, id=tweet["id"], mention=mention)
                
                # Create URL relationships
                for url in tweet.get("urls", []):
                    if url:
                        await session.run("""
                            MATCH (t:Tweet {id: $id})
                            MERGE (u:URL {url: $url})
                            MERGE (t)-[:CONTAINS_URL]->(u)
                        """, id=tweet["id"], url=url[:500])  # Limit URL length
                
                # Create theme relationships
                for theme in tweet.get("themes", []):
                    await session.run("""
                        MATCH (t:Tweet {id: $id})
                        MERGE (th:Theme {name: $theme})
                        MERGE (t)-[:ABOUT_THEME]->(th)
                    """, id=tweet["id"], theme=theme)
                
                # Create proper noun relationships
                for pn in tweet.get("proper_nouns", []):
                    await session.run("""
                        MATCH (t:Tweet {id: $id})
                        MERGE (e:Entity {name: $name})
                        SET e.type = 'proper_noun'
                        MERGE (t)-[:MENTIONS_ENTITY]->(e)
                    """, id=tweet["id"], name=pn)
                
                logger.info(f"Stored: {tweet['id']} - {len(tweet.get('hashtags', []))} hashtags, {len(tweet.get('themes', []))} themes, {len(tweet.get('proper_nouns', []))} entities")
    
    async def get_stats(self) -> Dict:
        """Get database statistics"""
        async with self.driver.session() as session:
            # Count nodes
            tweets = await session.run("MATCH (t:Tweet) RETURN count(t) as count")
            tweet_count = (await tweets.single())["count"]
            
            # Count relationships
            rels = await session.run("MATCH ()-[r]->() RETURN type(r) as type, count(r) as count ORDER BY count DESC")
            relationships = {}
            async for record in rels:
                relationships[record["type"]] = record["count"]
            
            # Count themes
            themes = await session.run("MATCH (th:Theme) RETURN count(th) as count")
            theme_count = (await themes.single())["count"]
            
            # Count entities
            entities = await session.run("MATCH (e:Entity) RETURN count(e) as count")
            entity_count = (await entities.single())["count"]
            
            return {
                "tweets": tweet_count,
                "themes": theme_count,
                "entities": entity_count,
                "relationships": relationships
            }
    
    async def run(self):
        """Run the complete pipeline"""
        print("\n" + "="*70)
        print("TWEET GRAPH - COMPLETE PIPELINE")
        print("="*70)
        
        # 1. Clear old tweets
        await self.clear_old_tweets()
        
        # 2. Fetch from browser (truncated)
        bookmarks = await self.fetch_browser_batch()
        
        if not bookmarks:
            logger.error("No bookmarks found!")
            return
        
        # 3. Enrich with API (if token available)
        if self.bearer_token:
            bookmarks = await self.enrich_with_api(bookmarks)
        else:
            logger.warning("No API token - storing truncated tweets only")
            # Extract themes from truncated text too
            for b in bookmarks:
                themes, pns = self.extract_themes_and_entities(b.get("text", ""))
                b["themes"] = themes
                b["proper_nouns"] = pns
        
        # 4. Store with relationships
        await self.store_with_relationships(bookmarks)
        
        # 5. Get stats
        stats = await self.get_stats()
        
        print("\n" + "="*70)
        print("PIPELINE COMPLETE")
        print("="*70)
        print(f"Tweets stored: {stats['tweets']}")
        print(f"Themes extracted: {stats['themes']}")
        print(f"Entities extracted: {stats['entities']}")
        print(f"\nRelationships:")
        for rel_type, count in stats["relationships"].items():
            print(f"  {rel_type}: {count}")
        print("="*70)
    
    async def close(self):
        await self.driver.close()

async def main():
    import os
    
    bearer_token = os.environ.get("TWITTER_BEARER_TOKEN")
    
    pipeline = BookmarkPipeline(bearer_token)
    try:
        await pipeline.run()
    finally:
        await pipeline.close()

if __name__ == "__main__":
    asyncio.run(main())
