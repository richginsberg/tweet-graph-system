# Deduplication logic

import logging
from typing import Dict, List, Optional
import httpx

logger = logging.getLogger(__name__)

TWEET_GRAPH_API_URL = "http://tweet-graph-api:8000"

async def check_tweet_exists(tweet_id: str) -> bool:
    """Check if tweet already exists in database"""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{TWEET_GRAPH_API_URL}/tweets/{tweet_id}",
                timeout=10.0
            )
            return response.status_code == 200
        except:
            return False

async def filter_new_tweets(tweets: List[Dict]) -> List[Dict]:
    """Filter out tweets that already exist"""
    new_tweets = []
    
    for tweet in tweets:
        tweet_id = tweet.get("id")
        if not tweet_id:
            continue
        
        exists = await check_tweet_exists(tweet_id)
        if not exists:
            new_tweets.append(tweet)
        else:
            logger.debug(f"Tweet {tweet_id} already exists, skipping")
    
    return new_tweets
