#!/usr/bin/env python3
"""
Capture tweet screenshots and optionally store in Neo4j or filesystem
"""

import asyncio
import sys
import os
from pathlib import Path
from playwright.async_api import async_playwright

SCREENSHOT_DIR = Path.home() / ".openclaw" / "workspace" / "tweet-graph-system" / "screenshots"
SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)

async def capture_tweet_screenshot(tweet_id: str, output_path: str = None) -> str:
    """
    Capture screenshot of a tweet embed
    
    Args:
        tweet_id: Twitter/X tweet ID
        output_path: Optional custom path (default: screenshots/{id}.png)
    
    Returns:
        Path to screenshot file
    """
    if not output_path:
        output_path = str(SCREENSHOT_DIR / f"{tweet_id}.png")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        # Set viewport
        await page.set_viewport_size({"width": 550, "height": 600})
        
        # Navigate to embed URL
        embed_url = f"https://platform.twitter.com/embed/Tweet.html?id={tweet_id}&theme=dark"
        await page.goto(embed_url, wait_until="networkidle")
        
        # Wait for tweet to load
        await page.wait_for_selector('article', timeout=10000)
        
        # Wait a bit for images/fonts
        await asyncio.sleep(2)
        
        # Take screenshot
        await page.screenshot(path=output_path, full_page=False)
        
        await browser.close()
    
    return output_path

async def capture_multiple(tweet_ids: list):
    """Capture screenshots for multiple tweets"""
    for tweet_id in tweet_ids:
        try:
            path = await capture_tweet_screenshot(tweet_id)
            print(f"✅ Captured: {tweet_id} → {path}")
        except Exception as e:
            print(f"❌ Failed: {tweet_id} - {e}")

# Example Neo4j integration (optional)
"""
# In Neo4j, store screenshot path as property:
MATCH (t:Tweet {id: $id})
SET t.screenshot_path = $path,
    t.screenshot_captured = datetime()

# Or store base64 (not recommended for large images):
import base64
with open(path, 'rb') as f:
    b64 = base64.b64encode(f.read()).decode()
MATCH (t:Tweet {id: $id})
SET t.screenshot_b64 = $b64  # Only for small images!
"""

def main():
    if len(sys.argv) < 2:
        print("Usage: python capture_screenshots.py <tweet_id> [tweet_id2 ...]")
        print("       python capture_screenshots.py all  # Capture all tweets in DB")
        sys.exit(1)
    
    if sys.argv[1] == "all":
        # Get all tweet IDs from API
        import requests
        resp = requests.get("http://localhost:8000/tweets")
        if resp.ok:
            tweets = resp.json()
            tweet_ids = [t["id"] for t in tweets if not t["id"].startswith("test")]
            print(f"Capturing {len(tweet_ids)} tweet screenshots...")
            asyncio.run(capture_multiple(tweet_ids))
    else:
        tweet_ids = sys.argv[1:]
        asyncio.run(capture_multiple(tweet_ids))

if __name__ == "__main__":
    main()
