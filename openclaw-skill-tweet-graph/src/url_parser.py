# URL Parser for Twitter/X URLs

import re
from typing import Optional, Dict

def parse_twitter_url(url: str) -> Optional[Dict[str, str]]:
    """Parse Twitter/X URL and extract components"""
    patterns = [
        r'twitter\.com/(?P<username>\w+)/status/(?P<id>\d+)',
        r'x\.com/(?P<username>\w+)/status/(?P<id>\d+)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return {
                "username": match.group("username"),
                "id": match.group("id"),
                "url": url
            }
    
    return None

def extract_tweet_id(url: str) -> Optional[str]:
    """Extract just the tweet ID from URL"""
    parsed = parse_twitter_url(url)
    return parsed["id"] if parsed else None

def is_twitter_url(url: str) -> bool:
    """Check if URL is a Twitter/X URL"""
    return "twitter.com" in url or "x.com" in url
