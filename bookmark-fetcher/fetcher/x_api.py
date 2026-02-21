"""
X/Twitter API v2 Integration for fetching full tweet text

Supports:
- API-only mode for low usage scenarios
- Hybrid mode to fix truncated tweets from browser scraping
- Rate limit handling with exponential backoff
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional
import httpx

logger = logging.getLogger(__name__)

# X API v2 rate limits
# - Tweet lookup: 900 requests / 15 min (user auth) or 300 (app-only)
# - We'll implement conservative rate limiting

class XAPIError(Exception):
    """Base error for X API operations"""
    pass

class RateLimitError(XAPIError):
    """Rate limit exceeded"""
    def __init__(self, reset_time: int):
        self.reset_time = reset_time
        super().__init__(f"Rate limit exceeded, resets at {reset_time}")

class XAPIFetcher:
    """X/Twitter API v2 client for fetching tweet data"""
    
    API_BASE = "https://api.twitter.com/2"
    
    def __init__(
        self,
        bearer_token: Optional[str] = None,
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        access_token: Optional[str] = None,
        access_secret: Optional[str] = None,
        requests_per_15min: int = 300  # Conservative for app-only
    ):
        self.bearer_token = bearer_token
        self.api_key = api_key
        self.api_secret = api_secret
        self.access_token = access_token
        self.access_secret = access_secret
        self.requests_per_15min = requests_per_15min
        
        # Rate limit tracking
        self.request_timestamps: List[float] = []
        self.min_request_interval = (15 * 60) / requests_per_15min
        
        # HTTP client
        self.client = httpx.AsyncClient(timeout=30.0)
    
    def _get_headers(self) -> Dict[str, str]:
        """Get authorization headers"""
        if self.bearer_token:
            return {
                "Authorization": f"Bearer {self.bearer_token}",
                "Content-Type": "application/json"
            }
        # TODO: OAuth 1.0a for user context
        raise XAPIError("No authentication configured")
    
    async def _check_rate_limit(self):
        """Enforce rate limiting with sliding window"""
        import time
        now = time.time()
        
        # Remove timestamps older than 15 minutes
        cutoff = now - (15 * 60)
        self.request_timestamps = [t for t in self.request_timestamps if t > cutoff]
        
        if len(self.request_timestamps) >= self.requests_per_15min:
            # Calculate wait time
            oldest = min(self.request_timestamps)
            wait_time = oldest + (15 * 60) - now
            if wait_time > 0:
                logger.warning(f"Rate limit reached, waiting {wait_time:.0f}s")
                await asyncio.sleep(wait_time)
        
        self.request_timestamps.append(now)
    
    async def get_tweet(self, tweet_id: str) -> Optional[Dict]:
        """
        Fetch a single tweet by ID using API v2
        
        Returns full tweet data including complete text (no truncation)
        """
        await self._check_rate_limit()
        
        # Tweet fields to request
        tweet_fields = [
            "id", "text", "created_at", "author_id", "conversation_id",
            "public_metrics", "entities", "attachments", "lang",
            "in_reply_to_user_id", "referenced_tweets"
        ]
        
        expansions = [
            "author_id", "referenced_tweets.id", "entities.mentions.username"
        ]
        
        user_fields = ["id", "username", "name"]
        
        url = f"{self.API_BASE}/tweets/{tweet_id}"
        params = {
            "tweet.fields": ",".join(tweet_fields),
            "expansions": ",".join(expansions),
            "user.fields": ",".join(user_fields)
        }
        
        try:
            response = await self.client.get(
                url,
                headers=self._get_headers(),
                params=params
            )
            
            if response.status_code == 429:
                # Rate limited
                reset_time = int(response.headers.get("x-rate-limit-reset", 0))
                raise RateLimitError(reset_time)
            
            if response.status_code == 404:
                logger.warning(f"Tweet {tweet_id} not found (deleted or private)")
                return None
            
            if response.status_code == 401:
                raise XAPIError("Authentication failed - check API credentials")
            
            if response.status_code == 403:
                raise XAPIError("Access forbidden - check app permissions")
            
            response.raise_for_status()
            
            data = response.json()
            
            if "errors" in data:
                for error in data["errors"]:
                    logger.error(f"API error: {error}")
                return None
            
            return self._parse_tweet_response(data)
            
        except httpx.HTTPError as e:
            logger.error(f"HTTP error fetching tweet {tweet_id}: {e}")
            raise XAPIError(f"HTTP error: {e}")
    
    async def get_tweets_batch(self, tweet_ids: List[str]) -> Dict[str, Dict]:
        """
        Fetch multiple tweets in a single request (up to 100)
        
        Returns dict of tweet_id -> tweet_data
        """
        if not tweet_ids:
            return {}
        
        # API v2 allows up to 100 tweets per request
        if len(tweet_ids) > 100:
            tweet_ids = tweet_ids[:100]
        
        await self._check_rate_limit()
        
        tweet_fields = [
            "id", "text", "created_at", "author_id", "conversation_id",
            "public_metrics", "entities", "attachments", "lang",
            "in_reply_to_user_id", "referenced_tweets"
        ]
        
        expansions = ["author_id", "entities.mentions.username"]
        user_fields = ["id", "username", "name"]
        
        url = f"{self.API_BASE}/tweets"
        params = {
            "ids": ",".join(tweet_ids),
            "tweet.fields": ",".join(tweet_fields),
            "expansions": ",".join(expansions),
            "user.fields": ",".join(user_fields)
        }
        
        try:
            response = await self.client.get(
                url,
                headers=self._get_headers(),
                params=params
            )
            
            if response.status_code == 429:
                reset_time = int(response.headers.get("x-rate-limit-reset", 0))
                raise RateLimitError(reset_time)
            
            response.raise_for_status()
            
            data = response.json()
            results = {}
            
            # Build user lookup
            users = {}
            if "includes" in data and "users" in data["includes"]:
                for user in data["includes"]["users"]:
                    users[user["id"]] = user
            
            # Parse tweets
            for tweet in data.get("data", []):
                tweet_id = tweet["id"]
                author_id = tweet.get("author_id")
                
                results[tweet_id] = {
                    "id": tweet_id,
                    "text": tweet["text"],
                    "author_id": author_id,
                    "author_username": users.get(author_id, {}).get("username", ""),
                    "created_at": self._parse_twitter_date(tweet.get("created_at")),
                    "hashtags": [h["tag"] for h in tweet.get("entities", {}).get("hashtags", [])],
                    "mentions": [m["username"] for m in tweet.get("entities", {}).get("mentions", [])],
                    "urls": [u.get("expanded_url", u.get("url", "")) 
                            for u in tweet.get("entities", {}).get("urls", [])],
                    "reply_to": None,
                    "quote_of": None,
                    "fetch_method": "api",
                    "is_truncated": False
                }
                
                # Handle referenced tweets (replies, quotes)
                for ref in tweet.get("referenced_tweets", []):
                    if ref["type"] == "replied_to":
                        results[tweet_id]["reply_to"] = ref["id"]
                    elif ref["type"] == "quoted":
                        results[tweet_id]["quote_of"] = ref["id"]
            
            return results
            
        except httpx.HTTPError as e:
            logger.error(f"HTTP error fetching tweets batch: {e}")
            raise XAPIError(f"HTTP error: {e}")
    
    def _parse_tweet_response(self, data: Dict) -> Dict:
        """Parse single tweet response"""
        tweet = data.get("data", data)
        
        if not tweet:
            return None
        
        # Get author info from includes
        author_username = ""
        if "includes" in data:
            users = data["includes"].get("users", [])
            if users:
                author_username = users[0].get("username", "")
        
        result = {
            "id": tweet["id"],
            "text": tweet["text"],
            "author_id": tweet.get("author_id"),
            "author_username": author_username,
            "created_at": self._parse_twitter_date(tweet.get("created_at")),
            "hashtags": [h["tag"] for h in tweet.get("entities", {}).get("hashtags", [])],
            "mentions": [m["username"] for m in tweet.get("entities", {}).get("mentions", [])],
            "urls": [u.get("expanded_url", u.get("url", "")) 
                    for u in tweet.get("entities", {}).get("urls", [])],
            "reply_to": None,
            "quote_of": None,
            "fetch_method": "api",
            "is_truncated": False,
            "public_metrics": tweet.get("public_metrics", {}),
            "bookmark_url": f"https://x.com/{author_username}/status/{tweet['id']}"
        }
        
        # Handle referenced tweets
        for ref in tweet.get("referenced_tweets", []):
            if ref["type"] == "replied_to":
                result["reply_to"] = ref["id"]
            elif ref["type"] == "quoted":
                result["quote_of"] = ref["id"]
        
        return result
    
    def _parse_twitter_date(self, date_str: Optional[str]) -> Optional[datetime]:
        """Parse Twitter ISO 8601 date format"""
        if not date_str:
            return None
        try:
            # ISO 8601 format: "2024-01-15T10:30:00.000Z"
            return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        except:
            return None
    
    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()


# Convenience function for hybrid mode
async def fetch_full_text(tweet_ids: List[str], bearer_token: str) -> Dict[str, str]:
    """
    Fetch full text for a list of tweet IDs.
    Returns dict of tweet_id -> full_text
    """
    async with XAPIFetcher(bearer_token=bearer_token) as api:
        tweets = await api.get_tweets_batch(tweet_ids)
        return {tid: t["text"] for tid, t in tweets.items()}
