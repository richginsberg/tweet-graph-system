# X/Twitter API v2 Client
# Fetches full tweet data including hashtags, mentions, URLs

import httpx
import logging
import re
from typing import Dict, List, Optional
from html.parser import HTMLParser

logger = logging.getLogger(__name__)


class TweetTextParser(HTMLParser):
    """Parse tweet text from oEmbed HTML"""
    def __init__(self):
        super().__init__()
        self.in_tweet = False
        self.text_parts = []
        
    def handle_starttag(self, tag, attrs):
        if tag == 'p' and ('class', 'twitter-tweet') in attrs:
            self.in_tweet = True
            
    def handle_endtag(self, tag):
        if tag == 'p' and self.in_tweet:
            self.in_tweet = False
            
    def handle_data(self, data):
        if self.in_tweet:
            self.text_parts.append(data)
    
    def get_text(self) -> str:
        return ''.join(self.text_parts).strip()


class TwitterAPIClient:
    """
    Twitter/X API v2 client for fetching full tweet data
    
    Free tier limits:
    - 500 posts/month (read)
    - Rate limit: 60 requests/15min
    
    Setup:
    1. Go to https://developer.twitter.com/en/portal/dashboard
    2. Create a project/app
    3. Get Bearer Token
    """
    
    def __init__(self, bearer_token: str):
        self.bearer_token = bearer_token
        self.base_url = "https://api.twitter.com/2"
    
    async def get_tweet(self, tweet_id: str) -> Optional[Dict]:
        """
        Get full tweet data by ID
        
        Returns:
        {
            "id": "123",
            "text": "Full tweet text with #hashtags @mentions",
            "author_id": "456",
            "author_username": "user",
            "hashtags": ["hashtags"],
            "mentions": ["mentions"],
            "urls": ["https://..."],
            "created_at": "2024-01-01T00:00:00Z"
        }
        """
        url = f"{self.base_url}/tweets/{tweet_id}"
        
        params = {
            "tweet.fields": "created_at,author_id,entities,public_metrics",
            "expansions": "author_id",
            "user.fields": "username,name"
        }
        
        headers = {
            "Authorization": f"Bearer {self.bearer_token}"
        }
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(url, params=params, headers=headers, timeout=30.0)
                
                if response.status_code == 200:
                    data = response.json()
                    return self._parse_tweet_response(data)
                elif response.status_code == 429:
                    logger.warning("Rate limited - waiting...")
                    return None
                else:
                    logger.error(f"API error {response.status_code}: {response.text}")
                    return None
                    
            except Exception as e:
                logger.error(f"API request failed: {e}")
                return None
    
    async def get_tweets_batch(self, tweet_ids: List[str]) -> List[Dict]:
        """
        Get multiple tweets (up to 100 at once)
        More efficient than individual calls
        """
        if not tweet_ids:
            return []
        
        url = f"{self.base_url}/tweets"
        
        params = {
            "ids": ",".join(tweet_ids[:100]),
            "tweet.fields": "created_at,author_id,entities,public_metrics",
            "expansions": "author_id",
            "user.fields": "username,name"
        }
        
        headers = {
            "Authorization": f"Bearer {self.bearer_token}"
        }
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(url, params=params, headers=headers, timeout=30.0)
                
                if response.status_code == 200:
                    data = response.json()
                    return self._parse_tweets_response(data)
                else:
                    logger.error(f"Batch API error: {response.status_code}")
                    return []
                    
            except Exception as e:
                logger.error(f"Batch request failed: {e}")
                return []
    
    def _parse_tweet_response(self, data: Dict) -> Optional[Dict]:
        """Parse single tweet response"""
        if "data" not in data:
            return None
        
        tweet = data["data"]
        
        # Get author info from includes
        author_username = ""
        if "includes" in data and "users" in data["includes"]:
            users = data["includes"]["users"]
            if users:
                author_username = users[0].get("username", "")
        
        # Extract entities
        entities = tweet.get("entities", {})
        
        hashtags = [h["tag"] for h in entities.get("hashtags", [])]
        mentions = [m["username"] for m in entities.get("mentions", [])]
        urls = [u["expanded_url"] if "expanded_url" in u else u["url"] 
                for u in entities.get("urls", [])]
        
        return {
            "id": tweet["id"],
            "text": tweet["text"],
            "author_id": tweet.get("author_id"),
            "author_username": author_username,
            "hashtags": hashtags,
            "mentions": mentions,
            "urls": urls,
            "created_at": tweet.get("created_at"),
            "truncated": False  # API v2 returns full text
        }
    
    def _parse_tweets_response(self, data: Dict) -> List[Dict]:
        """Parse batch tweets response"""
        if "data" not in data:
            return []
        
        # Build author lookup
        authors = {}
        if "includes" in data and "users" in data["includes"]:
            for user in data["includes"]["users"]:
                authors[user["id"]] = user.get("username", "")
        
        tweets = []
        for tweet in data["data"]:
            entities = tweet.get("entities", {})
            
            hashtags = [h["tag"] for h in entities.get("hashtags", [])]
            mentions = [m["username"] for m in entities.get("mentions", [])]
            urls = [u.get("expanded_url", u.get("url", "")) 
                    for u in entities.get("urls", [])]
            
            author_id = tweet.get("author_id")
            
            tweets.append({
                "id": tweet["id"],
                "text": tweet["text"],
                "author_id": author_id,
                "author_username": authors.get(author_id, ""),
                "hashtags": hashtags,
                "mentions": mentions,
                "urls": urls,
                "created_at": tweet.get("created_at"),
                "truncated": False
            })
        
        return tweets


async def get_tweet_via_oembed(tweet_id: str) -> Optional[Dict]:
    """
    Fetch tweet text via Twitter oEmbed API (free, no auth required)
    
    This is a workaround for the free tier which doesn't allow tweet lookup.
    The oEmbed API returns HTML that contains the full tweet text.
    
    Returns:
    {
        "id": "123",
        "text": "Full tweet text",
        "author_username": "user",
        "html": "<blockquote>...</blockquote>"
    }
    """
    url = "https://publish.twitter.com/oembed"
    
    params = {
        "url": f"https://twitter.com/user/status/{tweet_id}",
        "omit_script": "true",
        "dnt": "true"
    }
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, params=params, timeout=30.0)
            
            if response.status_code == 200:
                data = response.json()
                html = data.get("html", "")
                
                # Parse author username from the HTML
                author_username = ""
                author_match = re.search(r'twitter\.com/(\w+)/status/', html)
                if author_match:
                    author_username = author_match.group(1)
                
                # Parse text from HTML - extract from the blockquote
                # The tweet text is usually in the <p> or plain text before the link
                text = _extract_text_from_oembed(html, tweet_id)
                
                if not text:
                    logger.warning(f"Could not extract text from oEmbed for {tweet_id}")
                    return None
                
                return {
                    "id": tweet_id,
                    "text": text,
                    "author_username": author_username,
                    "html": html,
                    "truncated": False
                }
            else:
                logger.error(f"oEmbed API error {response.status_code}: {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"oEmbed request failed: {e}")
            return None


def _extract_text_from_oembed(html: str, tweet_id: str) -> Optional[str]:
    """Extract tweet text from oEmbed HTML"""
    
    # Method 1: Use HTML parser
    try:
        parser = TweetTextParser()
        parser.feed(html)
        text = parser.get_text()
        if text and len(text) > 10:
            # Clean up - remove the link at the end
            # Usually ends with "— Author (@username) Date" and link
            lines = text.split('\n')
            # Find where the attribution starts
            clean_lines = []
            for line in lines:
                if line.strip().startswith('—') or '(@' in line:
                    break
                clean_lines.append(line)
            
            text = ' '.join(clean_lines).strip()
            if text and len(text) > 10:
                return text
    except Exception as e:
        logger.debug(f"HTML parser failed: {e}")
    
    # Method 2: Regex extraction - find text between <p> tags
    p_match = re.search(r'<p[^>]*>(.*?)</p>', html, re.DOTALL)
    if p_match:
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', '', p_match.group(1))
        # Decode HTML entities
        text = text.replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')
        text = text.replace('&quot;', '"').replace('&#39;', "'")
        text = text.strip()
        if text and len(text) > 10:
            return text
    
    # Method 3: Just get all text content, remove the date/link pattern
    text = re.sub(r'<[^>]+>', ' ', html)
    text = text.replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')
    text = text.replace('&quot;', '"').replace('&#39;', "'")
    text = re.sub(r'\s+', ' ', text).strip()
    
    # Remove the trailing "— Author (@user) Date https://..." pattern
    text = re.sub(r'—\s*\w+\s*\(@\w+\).*$', '', text)
    text = re.sub(r'https?://.*$', '', text)
    
    return text.strip() if len(text.strip()) > 10 else None
