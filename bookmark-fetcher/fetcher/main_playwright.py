# Bookmark Fetcher with Playwright + Cookie Auth

import asyncio
import json
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
import httpx
from playwright.async_api import async_playwright

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TWEET_GRAPH_API_URL = "http://localhost:8000"
BOOKMARKS_URL = "https://x.com/i/bookmarks"
COOKIES_FILE = "cookies.json"
STATE_FILE = "state.json"

class BookmarkFetcher:
    def __init__(self):
        self.state = self.load_state()
        self.cookies = self.load_cookies()
    
    def load_state(self) -> Dict:
        try:
            with open(STATE_FILE, "r") as f:
                return json.load(f)
        except:
            return {"last_fetch": None, "last_tweet_id": None, "total_bookmarks": 0}
    
    def save_state(self):
        with open(STATE_FILE, "w") as f:
            json.dump(self.state, f, indent=2)
    
    def load_cookies(self) -> List[Dict]:
        """Load cookies from Chrome export"""
        try:
            with open(COOKIES_FILE, "r") as f:
                return json.load(f)
        except:
            logger.warning(f"No cookies file found at {COOKIES_FILE}")
            return []
    
    async def fetch_bookmarks_playwright(self) -> List[Dict]:
        """
        Fetch bookmarks using Playwright with stored cookies
        """
        logger.info("Fetching bookmarks via Playwright...")
        
        bookmarks = []
        
        async with async_playwright() as p:
            # Launch browser
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            
            # Add cookies if available
            if self.cookies:
                # Format cookies for Playwright
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
            
            # Navigate to bookmarks
            logger.info(f"Navigating to {BOOKMARKS_URL}")
            await page.goto(BOOKMARKS_URL, wait_until="networkidle")
            
            # Wait for tweets to load
            await page.wait_for_selector('[data-testid="tweet"]', timeout=30000)
            
            # Scroll to load more bookmarks
            for i in range(5):  # Scroll 5 times
                await page.evaluate("window.scrollBy(0, 1000)")
                await asyncio.sleep(2)
                logger.info(f"Scrolled {i+1}/5")
            
            # Extract tweet data
            tweets = await page.query_selector_all('[data-testid="tweet"]')
            logger.info(f"Found {len(tweets)} tweets")
            
            for tweet in tweets[:50]:  # Limit to 50
                try:
                    tweet_data = await self.parse_tweet_element(page, tweet)
                    if tweet_data.get("id"):
                        bookmarks.append(tweet_data)
                except Exception as e:
                    logger.debug(f"Failed to parse tweet: {e}")
            
            await browser.close()
        
        logger.info(f"Parsed {len(bookmarks)} bookmarks")
        return bookmarks
    
    async def parse_tweet_element(self, page, tweet_element) -> Dict:
        """Parse tweet data from Playwright element"""
        try:
            # Get tweet link
            link = await tweet_element.query_selector('a[href*="/status/"]')
            if not link:
                return {}
            
            href = await link.get_attribute("href")
            # Extract tweet ID from URL
            tweet_id = href.split("/status/")[-1].split("?")[0]
            
            # Get tweet text
            text_elem = await tweet_element.query_selector('[data-testid="tweetText"]')
            text = await text_elem.inner_text() if text_elem else ""
            
            # Get author
            author_elem = await tweet_element.query_selector('[data-testid="User-Name"]')
            author = await author_elem.inner_text() if author_elem else ""
            author_username = author.split("@")[-1].split("\n")[0] if author else ""
            
            # Extract hashtags and mentions from text
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
        """Sync bookmarks to Neo4j via API"""
        logger.info(f"Syncing {len(bookmarks)} bookmarks...")
        
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
    
    async def run(self):
        """Main fetch and sync loop"""
        logger.info("Starting bookmark fetch...")
        
        try:
            # Fetch bookmarks
            bookmarks = await self.fetch_bookmarks_playwright()
            
            if not bookmarks:
                logger.warning("No bookmarks found - check cookies authentication")
                return {"error": "No bookmarks found"}
            
            # Sync to graph
            result = await self.sync_to_graph(bookmarks)
            
            # Update state
            self.state["last_fetch"] = datetime.utcnow().isoformat()
            self.state["total_bookmarks"] = len(bookmarks)
            if bookmarks:
                self.state["last_tweet_id"] = bookmarks[0].get("id")
            self.save_state()
            
            logger.info(f"Sync complete: {result}")
            return result
            
        except Exception as e:
            logger.error(f"Fetch failed: {e}")
            return {"error": str(e)}

async def main():
    fetcher = BookmarkFetcher()
    await fetcher.run()

if __name__ == "__main__":
    asyncio.run(main())
