"""
Bookmark Fetcher - Fetch limited batch (10 bookmarks)
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import List, Dict, Any
import httpx
from playwright.async_api import async_playwright

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

TWEET_GRAPH_API_URL = "http://localhost:8000"
BOOKMARKS_URL = "https://x.com/i/bookmarks"
COOKIES_FILE = "cookies.json"
BATCH_LIMIT = 10  # Only fetch 10 for testing

class BookmarkFetcher:
    def __init__(self):
        self.cookies = self.load_cookies()
    
    def load_cookies(self) -> List[Dict]:
        try:
            with open(COOKIES_FILE, "r") as f:
                return json.load(f)
        except:
            logger.warning(f"No cookies file found at {COOKIES_FILE}")
            return []
    
    async def fetch_bookmarks(self) -> List[Dict]:
        logger.info("Fetching bookmarks via Playwright...")
        
        bookmarks = []
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            
            if self.cookies:
                formatted_cookies = []
                for cookie in self.cookies:
                    formatted_cookies.append({
                        "name": cookie.get("name", ""),
                        "value": cookie.get("value", ""),
                        "domain": cookie.get("domain", ".x.com"),
                        "path": cookie.get("path", "/"),
                    })
                await context.add_cookies(formatted_cookies)
                logger.info(f"Loaded {len(formatted_cookies)} cookies")
            
            page = await context.new_page()
            
            logger.info(f"Navigating to {BOOKMARKS_URL}")
            await page.goto(BOOKMARKS_URL, wait_until="networkidle")
            
            # Wait for tweets
            await page.wait_for_selector('[data-testid="tweet"]', timeout=30000)
            logger.info("Tweets loaded")
            
            # Scroll a bit to load more
            for i in range(2):
                await page.evaluate("window.scrollBy(0, 1000)")
                await asyncio.sleep(1)
            
            # Extract tweets
            tweets = await page.query_selector_all('[data-testid="tweet"]')
            logger.info(f"Found {len(tweets)} tweets on page")
            
            for tweet in tweets[:BATCH_LIMIT]:
                try:
                    tweet_data = await self.parse_tweet_element(page, tweet)
                    if tweet_data.get("id"):
                        bookmarks.append(tweet_data)
                        logger.info(f"Parsed: {tweet_data['id']} - {tweet_data['text'][:50]}...")
                except Exception as e:
                    logger.debug(f"Failed to parse tweet: {e}")
            
            await browser.close()
        
        logger.info(f"Parsed {len(bookmarks)} bookmarks")
        return bookmarks
    
    async def parse_tweet_element(self, page, tweet_element) -> Dict:
        try:
            link = await tweet_element.query_selector('a[href*="/status/"]')
            if not link:
                return {}
            
            href = await link.get_attribute("href")
            tweet_id = href.split("/status/")[-1].split("?")[0]
            
            text_elem = await tweet_element.query_selector('[data-testid="tweetText"]')
            text = await text_elem.inner_text() if text_elem else ""
            
            author_elem = await tweet_element.query_selector('[data-testid="User-Name"]')
            author = await author_elem.inner_text() if author_elem else ""
            author_username = author.split("@")[-1].split("\n")[0] if author else ""
            
            hashtags = [word[1:] for word in text.split() if word.startswith("#")]
            mentions = [word[1:] for word in text.split() if word.startswith("@")]
            
            return {
                "id": tweet_id,
                "text": text,
                "author_username": author_username,
                "hashtags": hashtags,
                "mentions": mentions,
                "urls": [],
                "created_at": datetime.utcnow().isoformat(),
                "bookmark_url": f"https://x.com{href}"
            }
        except Exception as e:
            logger.debug(f"Parse error: {e}")
            return {}
    
    async def sync_to_graph(self, bookmarks: List[Dict]) -> Dict:
        logger.info(f"Syncing {len(bookmarks)} bookmarks to graph...")
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{TWEET_GRAPH_API_URL}/bookmarks/sync",
                json={"bookmarks": bookmarks},
                timeout=60.0
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Sync failed: {response.text}")
                return {"error": response.text}

async def main():
    fetcher = BookmarkFetcher()
    
    # Fetch
    bookmarks = await fetcher.fetch_bookmarks()
    
    if not bookmarks:
        logger.error("No bookmarks found - check cookies")
        return
    
    # Show what we got
    print("\n" + "="*60)
    print("BOOKMARKS FOUND:")
    print("="*60)
    for i, b in enumerate(bookmarks, 1):
        print(f"\n{i}. ID: {b['id']}")
        print(f"   Author: @{b['author_username']}")
        print(f"   Text: {b['text'][:100]}...")
        print(f"   Hashtags: {b['hashtags']}")
        print(f"   Mentions: {b['mentions']}")
    
    print("\n" + "="*60)
    
    # Sync to graph
    result = await fetcher.sync_to_graph(bookmarks)
    print(f"\nSync result: {result}")

if __name__ == "__main__":
    asyncio.run(main())
