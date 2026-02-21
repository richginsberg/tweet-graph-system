# X/Twitter API v2 Client
# Fetches full tweet data including hashtags, mentions, URLs

import httpx
import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

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
