"""
Bookmark Fetcher - Full fetch with proper pagination and incremental support

Modes:
- full: Load ALL bookmarks (aggressive scrolling)
- incremental: Load only new bookmarks since last fetch

Usage:
  python -m fetcher.main_playwright              # incremental (default)
  python -m fetcher.main_playwright --full       # full fetch
"""

import asyncio
import json
import logging
import re
import argparse
from datetime import datetime, timezone
from typing import List, Dict, Set, Optional
import httpx
from playwright.async_api import async_playwright

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

TWEET_GRAPH_API_URL = "http://localhost:8000"
BOOKMARKS_URL = "https://x.com/i/bookmarks"
COOKIES_FILE = "cookies.json"
STATE_FILE = "state.json"

# Scroll configuration
MAX_SCROLLS_FULL = 500          # For full fetch (increased)
MAX_SCROLLS_INCREMENTAL = 50    # For incremental
SCROLL_DISTANCE = 5000          # Pixels to scroll (increased)
SCROLL_DELAY = 3.0              # Seconds between scrolls (slightly longer)
NO_CHANGE_LIMIT = 15            # Stop after N scrolls with no new tweets (increased)


class BookmarkFetcher:
    def __init__(self, mode: str = "incremental"):
        self.mode = mode
        self.cookies = self.load_cookies()
        self.state = self.load_state()
        self.seen_ids: Set[str] = set()
        self.last_known_id: Optional[str] = None
    
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
            return {
                "last_fetch": None, 
                "last_tweet_id": None,
                "seen_tweet_ids": [],
                "total_bookmarks": 0,
                "mode": "incremental"
            }
    
    def save_state(self, count: int, new_ids: List[str] = None):
        """Save state after fetch"""
        self.state["last_fetch"] = datetime.now(timezone.utc).isoformat()
        self.state["total_bookmarks"] = count
        
        if new_ids:
            # Keep last 1000 seen IDs for incremental detection
            all_seen = list(self.seen_ids)
            self.state["seen_tweet_ids"] = all_seen[-1000:]
            if new_ids:
                self.state["last_tweet_id"] = new_ids[0]
        
        with open(STATE_FILE, "w") as f:
            json.dump(self.state, f, indent=2)
        
        logger.info(f"State saved: {len(self.seen_ids)} total seen IDs")
    
    def load_seen_ids(self):
        """Load previously seen tweet IDs for incremental mode"""
        if self.mode == "incremental":
            self.seen_ids = set(self.state.get("seen_tweet_ids", []))
            self.last_known_id = self.state.get("last_tweet_id")
            logger.info(f"Incremental mode: {len(self.seen_ids)} previously seen IDs")
    
    async def fetch_bookmarks(self) -> List[Dict]:
        """Fetch bookmarks with proper pagination"""
        logger.info(f"Fetching bookmarks (mode={self.mode})...")
        
        self.load_seen_ids()
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
            logger.info("Tweets loaded, starting scroll cycle...")
            
            # Determine max scrolls based on mode
            max_scrolls = MAX_SCROLLS_FULL if self.mode == "full" else MAX_SCROLLS_INCREMENTAL
            
            # Track scroll progress - we collect DURING scrolling, not after!
            # X lazy-loads and removes old tweets from DOM, so we must capture as we scroll
            collected_tweets: Dict[str, Dict] = {}  # id -> tweet data
            last_total_count = 0
            no_new_count = 0
            scroll_attempt = 0
            found_existing = False
            
            while scroll_attempt < max_scrolls:
                # First, parse tweets currently visible and collect them
                tweets = await page.query_selector_all('[data-testid="tweet"]')
                new_this_scroll = 0
                
                for tweet_elem in tweets:
                    try:
                        data = await self.parse_tweet(tweet_elem)
                        if data.get("id") and data.get("text"):
                            tweet_id = data["id"]
                            
                            # Skip if already collected
                            if tweet_id in collected_tweets:
                                continue
                            
                            # For incremental: check if we've hit existing
                            if self.mode == "incremental" and tweet_id in self.seen_ids:
                                logger.info(f"Found existing tweet {tweet_id} - stopping incremental fetch")
                                found_existing = True
                                break
                            
                            collected_tweets[tweet_id] = data
                            new_this_scroll += 1
                    except Exception as e:
                        logger.debug(f"Parse error during scroll: {e}")
                
                if found_existing:
                    break
                
                # Log progress
                total_collected = len(collected_tweets)
                logger.info(f"Scroll {scroll_attempt + 1}/{max_scrolls}: {len(tweets)} in view, {new_this_scroll} new, {total_collected} total collected")
                
                # Check if we're making progress
                if total_collected == last_total_count:
                    no_new_count += 1
                    if no_new_count >= NO_CHANGE_LIMIT:
                        logger.info(f"No new tweets after {NO_CHANGE_LIMIT} scrolls - reached end")
                        break
                else:
                    no_new_count = 0
                
                last_total_count = total_collected
                
                # Scroll down
                await page.evaluate(f"window.scrollBy(0, {SCROLL_DISTANCE})")
                await asyncio.sleep(SCROLL_DELAY)
                scroll_attempt += 1
            
            await browser.close()
            
            # Convert collected tweets to list
            new_bookmarks = list(collected_tweets.values())
            logger.info(f"Total collected: {len(new_bookmarks)} new bookmarks")
            bookmarks = new_bookmarks
        
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
        
        # Check for "Show more" link and click it to expand full text
        show_more_link = await elem.query_selector('[data-testid="tweet-text-show-more-link"]')
        if show_more_link:
            try:
                await show_more_link.click(timeout=2000)
                await asyncio.sleep(0.3)  # Wait for text to expand
                # Re-read the text element after expansion
                text = await text_elem.inner_text()
                is_truncated = False
            except Exception as e:
                # If click fails, mark as truncated
                logger.debug(f"Could not expand tweet {tweet_id}: {e}")
                text = await text_elem.inner_text()
                is_truncated = True
        else:
            text = await text_elem.inner_text()
            is_truncated = False
        
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
        
        # Note: is_truncated is already set above based on "Show more" link presence
        # If we successfully expanded the tweet, is_truncated = False
        # If expansion failed or link was present but couldn't click, is_truncated = True
        
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
        
        if not bookmarks:
            return {"total_received": 0, "new_stored": 0, "message": "No new bookmarks"}
        
        # Split into batches to avoid timeout
        batch_size = 50
        total_new = 0
        total_updated = 0
        
        async with httpx.AsyncClient() as client:
            for i in range(0, len(bookmarks), batch_size):
                batch = bookmarks[i:i+batch_size]
                logger.info(f"Syncing batch {i//batch_size + 1} ({len(batch)} tweets)...")
                
                response = await client.post(
                    f"{TWEET_GRAPH_API_URL}/bookmarks/sync",
                    json={"bookmarks": batch},
                    timeout=120.0
                )
                
                if response.status_code == 200:
                    result = response.json()
                    total_new += result.get("new_stored", 0)
                    total_updated += result.get("updated", 0)
                else:
                    logger.error(f"Sync failed: {response.text}")
                    return {"error": response.text}
        
        return {
            "total_received": len(bookmarks),
            "new_stored": total_new,
            "updated": total_updated
        }


async def main():
    parser = argparse.ArgumentParser(description="Fetch X/Twitter bookmarks")
    parser.add_argument("--full", action="store_true", help="Full fetch (load all bookmarks)")
    parser.add_argument("--incremental", action="store_true", help="Incremental fetch (only new)")
    args = parser.parse_args()
    
    mode = "full" if args.full else "incremental"
    fetcher = BookmarkFetcher(mode=mode)
    
    bookmarks = await fetcher.fetch_bookmarks()
    
    if not bookmarks:
        logger.info("No new bookmarks found")
        # Still update state
        fetcher.save_state(len(fetcher.seen_ids))
        return
    
    # Show summary
    print("\n" + "="*70)
    print(f"BOOKMARKS FETCHED ({mode} mode):")
    print("="*70)
    print(f"Total new: {len(bookmarks)}")
    
    # Show first few
    for i, b in enumerate(bookmarks[:5], 1):
        print(f"\n{i}. ID: {b['id']}")
        print(f"   Author: @{b['author_username']}")
        print(f"   Text: {b['text'][:100]}...")
        print(f"   Truncated: {b['truncated']}")
    
    if len(bookmarks) > 5:
        print(f"\n... and {len(bookmarks) - 5} more")
    
    print("\n" + "="*70)
    
    # Sync to graph
    result = await fetcher.sync_to_graph(bookmarks)
    
    # Save state with new IDs
    new_ids = [b["id"] for b in bookmarks]
    fetcher.save_state(len(fetcher.seen_ids), new_ids)
    
    print(f"\nSync result: {result}")
    print(f"State saved: {len(fetcher.seen_ids)} total seen tweet IDs")
    print("="*70)


if __name__ == "__main__":
    asyncio.run(main())
