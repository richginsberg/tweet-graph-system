"""
Bookmark Fetcher - Hybrid mode with X API v2 integration

Supports three modes:
- browser: Browser scraping only (marks truncated tweets)
- api: X API v2 only (requires API key, low usage)
- hybrid: Browser scraping + API to fix truncated tweets

Configuration via environment variables:
- FETCH_MODE: browser | api | hybrid (default: browser)
- X_BEARER_TOKEN: X API v2 bearer token (required for api/hybrid modes)
- TRUNCATION_INDICATORS: Characters that indicate truncated text (default: "…")
"""

import asyncio
import json
import logging
import os
import re
from datetime import datetime, timezone
from typing import List, Dict, Optional
import httpx
from playwright.async_api import async_playwright

from .x_api import XAPIFetcher, XAPIError, RateLimitError

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

TWEET_GRAPH_API_URL = os.getenv("TWEET_GRAPH_API_URL", "http://localhost:8000")
BOOKMARKS_URL = "https://x.com/i/bookmarks"
COOKIES_FILE = os.getenv("COOKIES_FILE", "cookies.json")
STATE_FILE = os.getenv("STATE_FILE", "state.json")

# Fetch mode configuration
FETCH_MODE = os.getenv("FETCH_MODE", "browser")  # browser | api | hybrid
X_BEARER_TOKEN = os.getenv("X_BEARER_TOKEN", "")
TRUNCATION_INDICATORS = os.getenv("TRUNCATION_INDICATORS", "…,>>>,[more]").split(",")

# Labels for truncated posts
TRUNCATED_LABEL = "📖 [TRUNCATED - click bookmark for full text]"
TRUNCATED_TAG = "__truncated__"


def is_truncated(text: str) -> bool:
    """Check if tweet text appears to be truncated"""
    for indicator in TRUNCATION_INDICATORS:
        indicator = indicator.strip()
        if indicator and indicator in text:
            return True
    # Also check if text ends abruptly without punctuation
    if text and text[-1] not in ".!?…\"')]" and len(text) > 280:
        return True
    return False


class BookmarkFetcher:
    def __init__(self, mode: str = None):
        self.mode = mode or FETCH_MODE
        self.cookies = self.load_cookies()
        self.state = self.load_state()
        self.api_fetcher: Optional[XAPIFetcher] = None
        
        if self.mode in ("api", "hybrid") and X_BEARER_TOKEN:
            self.api_fetcher = XAPIFetcher(bearer_token=X_BEARER_TOKEN)
            logger.info(f"X API v2 initialized for {self.mode} mode")
        elif self.mode in ("api", "hybrid"):
            logger.warning(f"Mode is '{self.mode}' but X_BEARER_TOKEN not set - falling back to browser")
            self.mode = "browser"
    
    def load_cookies(self) -> List[Dict]:
        try:
            with open(COOKIES_FILE, "r") as f:
                return json.load(f)
        except:
            logger.warning(f"No cookies file at {COOKIES_FILE}")
            return []
    
    def load_state(self) -> Dict:
        try:
            with open(STATE_FILE, "r") as f:
                return json.load(f)
        except:
            return {"last_fetch": None, "last_tweet_id": None, "total_bookmarks": 0, "mode": self.mode}
    
    def save_state(self, count: int, last_id: str = None, truncated_count: int = 0):
        self.state["last_fetch"] = datetime.now(timezone.utc).isoformat()
        self.state["total_bookmarks"] = count
        self.state["truncated_count"] = truncated_count
        self.state["mode"] = self.mode
        if last_id:
            self.state["last_tweet_id"] = last_id
        with open(STATE_FILE, "w") as f:
            json.dump(self.state, f, indent=2)
    
    async def fetch_bookmarks_api_only(self) -> List[Dict]:
        """
        API-only mode: Requires pre-fetched bookmark IDs.
        Note: X API v2 doesn't have a bookmarks endpoint, so this mode
        is primarily for enriching already-known tweet IDs.
        """
        logger.warning("API-only mode: X API v2 doesn't support bookmarks endpoint")
        logger.info("Use browser or hybrid mode for bookmark fetching")
        logger.info("API-only mode is for enriching existing tweet IDs")
        
        # This would need to be called with known tweet IDs
        return []
    
    async def fetch_bookmarks_browser(self) -> List[Dict]:
        """Fetch bookmarks via browser scraping"""
        logger.info("Fetching bookmarks via browser...")
        
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
            logger.info(f"Navigating to {BOOKMARKS_URL}")
            await page.goto(BOOKMARKS_URL, wait_until="networkidle")
            
            await page.wait_for_selector('[data-testid="tweet"]', timeout=30000)
            logger.info("Tweets loaded, scrolling to load all...")
            
            # Scroll multiple times
            last_count = 0
            scroll_attempts = 0
            max_scrolls = 20
            
            while scroll_attempts < max_scrolls:
                await page.evaluate("window.scrollBy(0, 2000)")
                await asyncio.sleep(2)
                
                tweets = await page.query_selector_all('[data-testid="tweet"]')
                current_count = len(tweets)
                logger.info(f"Scroll {scroll_attempts + 1}: {current_count} tweets visible")
                
                if current_count == last_count:
                    break
                last_count = current_count
                scroll_attempts += 1
            
            # Parse all tweets
            tweets = await page.query_selector_all('[data-testid="tweet"]')
            logger.info(f"Found {len(tweets)} total tweets")
            
            for tweet_elem in tweets:
                try:
                    data = await self.parse_tweet(tweet_elem)
                    if data.get("id") and data.get("text"):
                        # Check for truncation
                        data["is_truncated"] = is_truncated(data["text"])
                        data["fetch_method"] = "browser"
                        
                        if data["is_truncated"]:
                            logger.info(f"Truncated: {data['id']}")
                        
                        bookmarks.append(data)
                        logger.info(f"Parsed: {data['id']} - @{data['author_username']}")
                except Exception as e:
                    logger.error(f"Parse error: {e}")
            
            await browser.close()
        
        logger.info(f"Parsed {len(bookmarks)} bookmarks")
        return bookmarks
    
    async def fetch_bookmarks_hybrid(self) -> List[Dict]:
        """
        Hybrid mode: Browser scrape + API to fix truncated tweets
        """
        # First, get all bookmarks via browser
        bookmarks = await self.fetch_bookmarks_browser()
        
        # Find truncated tweets
        truncated_ids = [b["id"] for b in bookmarks if b.get("is_truncated")]
        
        if not truncated_ids:
            logger.info("No truncated tweets found")
            return bookmarks
        
        logger.info(f"Found {len(truncated_ids)} truncated tweets, fetching full text via API...")
        
        # Fetch full text via API
        try:
            full_tweets = await self.api_fetcher.get_tweets_batch(truncated_ids)
            
            # Update bookmarks with full text
            for bookmark in bookmarks:
                if bookmark["id"] in full_tweets:
                    full_data = full_tweets[bookmark["id"]]
                    bookmark["text"] = full_data["text"]
                    bookmark["is_truncated"] = False
                    bookmark["fetch_method"] = "hybrid"
                    # Also update entities if they were incomplete
                    if not bookmark.get("hashtags"):
                        bookmark["hashtags"] = full_data.get("hashtags", [])
                    if not bookmark.get("mentions"):
                        bookmark["mentions"] = full_data.get("mentions", [])
                    logger.info(f"Fixed truncated tweet: {bookmark['id']}")
        
        except RateLimitError as e:
            logger.warning(f"API rate limit hit, some tweets remain truncated: {e}")
        except XAPIError as e:
            logger.error(f"API error, some tweets remain truncated: {e}")
        
        return bookmarks
    
    async def fetch_bookmarks(self) -> List[Dict]:
        """Main entry point - fetch bookmarks based on configured mode"""
        if self.mode == "api":
            return await self.fetch_bookmarks_api_only()
        elif self.mode == "hybrid":
            return await self.fetch_bookmarks_hybrid()
        else:
            return await self.fetch_bookmarks_browser()
    
    async def parse_tweet(self, elem) -> Dict:
        """Parse tweet with full text and entities"""
        
        # Get tweet link and ID
        link = await elem.query_selector('a[href*="/status/"]')
        if not link:
            return {}
        href = await link.get_attribute("href")
        tweet_id = href.split("/status/")[-1].split("?")[0]
        
        # Get full text
        text_elem = await elem.query_selector('[data-testid="tweetText"]')
        if not text_elem:
            return {"id": tweet_id}
        
        text = await text_elem.inner_text()
        
        # Get author username
        author_username = ""
        author_elem = await elem.query_selector('[data-testid="User-Name"]')
        if author_elem:
            author_text = await author_elem.inner_text()
            parts = author_text.split("@")
            if len(parts) > 1:
                author_username = parts[1].split("\n")[0].strip()
        
        # Extract entities from text
        hashtags = list(set(re.findall(r'#(\w+)', text)))
        mentions = list(set(re.findall(r'@(\w+)', text)))
        
        # Get URLs from actual link elements
        urls = []
        url_links = await elem.query_selector_all('a[href^="http"]')
        for url_link in url_links:
            url = await url_link.get_attribute("href")
            if url and not "x.com/status" in url:
                if "?" in url:
                    url = url.split("?")[0]
                urls.append(url)
        
        urls = list(set(urls))[:5]
        
        return {
            "id": tweet_id,
            "text": text,
            "author_username": author_username,
            "hashtags": hashtags,
            "mentions": mentions,
            "urls": urls,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "bookmark_url": f"https://x.com{href}",
            "is_truncated": False,  # Will be set by caller
            "fetch_method": "browser"  # Will be updated if hybrid
        }
    
    async def sync_to_graph(self, bookmarks: List[Dict]) -> Dict:
        logger.info(f"Syncing {len(bookmarks)} bookmarks...")
        
        # Add truncated label to text for truncated posts
        for b in bookmarks:
            if b.get("is_truncated"):
                b["text"] = f"{TRUNCATED_LABEL}\n\n{b['text']}"
                if TRUNCATED_TAG not in b.get("hashtags", []):
                    b["hashtags"] = b.get("hashtags", []) + [TRUNCATED_TAG]
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{TWEET_GRAPH_API_URL}/bookmarks/sync",
                json={"bookmarks": bookmarks},
                timeout=120.0
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Sync failed: {response.text}")
                return {"error": response.text}
    
    async def close(self):
        if self.api_fetcher:
            await self.api_fetcher.close()


async def main():
    fetcher = BookmarkFetcher()
    
    try:
        bookmarks = await fetcher.fetch_bookmarks()
        
        if not bookmarks:
            logger.error("No bookmarks found")
            return
        
        # Count truncated
        truncated_count = sum(1 for b in bookmarks if b.get("is_truncated"))
        
        # Show what we found
        print("\n" + "="*70)
        print(f"BOOKMARKS FETCHED (mode: {fetcher.mode}):")
        print("="*70)
        for i, b in enumerate(bookmarks, 1):
            truncated_marker = " 📖[TRUNCATED]" if b.get("is_truncated") else ""
            print(f"\n{i}. ID: {b['id']}{truncated_marker}")
            print(f"   Author: @{b['author_username']}")
            print(f"   Text: {b['text'][:150]}...")
            print(f"   Hashtags: {b['hashtags']}")
            print(f"   Mentions: {b['mentions']}")
            print(f"   URLs: {len(b['urls'])}")
            print(f"   Fetch: {b.get('fetch_method', 'browser')}")
        
        print("\n" + "="*70)
        print(f"Total: {len(bookmarks)} | Truncated: {truncated_count}")
        print("="*70)
        
        # Sync to graph
        result = await fetcher.sync_to_graph(bookmarks)
        
        # Save state
        last_id = bookmarks[0]["id"] if bookmarks else None
        fetcher.save_state(len(bookmarks), last_id, truncated_count)
        
        print(f"\nSync result: {result}")
        print("="*70)
    
    finally:
        await fetcher.close()


if __name__ == "__main__":
    asyncio.run(main())
