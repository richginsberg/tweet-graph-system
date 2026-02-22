"""
Bookmark Fetcher - Full fetch with proper entity extraction
"""

import asyncio
import json
import logging
import re
from datetime import datetime, timezone
from typing import List, Dict
import httpx
from playwright.async_api import async_playwright

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

TWEET_GRAPH_API_URL = "http://localhost:8000"
BOOKMARKS_URL = "https://x.com/i/bookmarks"
COOKIES_FILE = "cookies.json"
STATE_FILE = "state.json"

class BookmarkFetcher:
    def __init__(self):
        self.cookies = self.load_cookies()
        self.state = self.load_state()
    
    def load_cookies(self) -> List[Dict]:
        try:
            with open(COOKIES_FILE, "r") as f:
                return json.load(f)
        except:
            logger.warning(f"No cookies file")
            return []
    
    def load_state(self) -> Dict:
        try:
            with open(STATE_FILE, "r") as f:
                return json.load(f)
        except:
            return {"last_fetch": None, "last_tweet_id": None, "total_bookmarks": 0}
    
    def save_state(self, count: int, last_id: str = None):
        self.state["last_fetch"] = datetime.now(timezone.utc).isoformat()
        self.state["total_bookmarks"] = count
        if last_id:
            self.state["last_tweet_id"] = last_id
        with open(STATE_FILE, "w") as f:
            json.dump(self.state, f, indent=2)
    
    async def fetch_bookmarks(self) -> List[Dict]:
        logger.info("Fetching ALL bookmarks...")
        
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
                        bookmarks.append(data)
                        logger.info(f"Parsed: {data['id']} - @{data['author_username']}")
                except Exception as e:
                    logger.error(f"Parse error: {e}")
            
            await browser.close()
        
        logger.info(f"Parsed {len(bookmarks)} bookmarks")
        return bookmarks
    
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
            # Extract username - usually after @
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
                # Clean up URL (remove tracking params)
                if "?" in url:
                    url = url.split("?")[0]
                urls.append(url)
        
        # Remove duplicates
        urls = list(set(urls))[:5]
        
        # Detect if tweet is actually truncated
        # Truncation indicators: ellipsis at end, cutoff mid-sentence, etc.
        text_stripped = text.strip()
        is_truncated = False
        truncation_indicators = ["…", "...", " [more]", ">>"]
        
        # Check for truncation indicators at end
        for indicator in truncation_indicators:
            if text_stripped.endswith(indicator):
                is_truncated = True
                break
        
        # Also check if longer text seems cutoff (no punctuation at end)
        # Only flag if it's a substantial tweet that ends abruptly
        if not is_truncated and len(text_stripped) > 200:
            last_char = text_stripped[-1]
            if last_char not in ".!?…\"')]\n":
                is_truncated = True
        
        return {
            "id": tweet_id,
            "text": text,
            "author_username": author_username,
            "hashtags": hashtags,
            "mentions": mentions,
            "urls": urls,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "bookmark_url": f"https://x.com{href}",
            "truncated": is_truncated
        }
    
    async def sync_to_graph(self, bookmarks: List[Dict]) -> Dict:
        logger.info(f"Syncing {len(bookmarks)} bookmarks...")
        
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

async def main():
    fetcher = BookmarkFetcher()
    
    bookmarks = await fetcher.fetch_bookmarks()
    
    if not bookmarks:
        logger.error("No bookmarks found")
        return
    
    # Show what we found
    print("\n" + "="*70)
    print("BOOKMARKS FETCHED:")
    print("="*70)
    for i, b in enumerate(bookmarks, 1):
        print(f"\n{i}. ID: {b['id']}")
        print(f"   Author: @{b['author_username']}")
        print(f"   Text: {b['text'][:150]}...")
        print(f"   Hashtags: {b['hashtags']}")
        print(f"   Mentions: {b['mentions']}")
        print(f"   URLs: {len(b['urls'])}")
    print("\n" + "="*70)
    
    # Sync to graph
    result = await fetcher.sync_to_graph(bookmarks)
    
    # Save state
    last_id = bookmarks[0]["id"] if bookmarks else None
    fetcher.save_state(len(bookmarks), last_id)
    
    print(f"\nSync result: {result}")
    print("="*70)

if __name__ == "__main__":
    asyncio.run(main())
