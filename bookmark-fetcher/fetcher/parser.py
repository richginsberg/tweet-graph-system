# Tweet Parser - Parse tweet data from various sources

import re
from typing import Dict, List, Optional
from datetime import datetime

def parse_tweet_from_html(html: str) -> Dict:
    """Parse tweet data from HTML"""
    # This would use BeautifulSoup or similar
    return {
        "id": "",
        "text": "",
        "author_username": "",
        "hashtags": [],
        "mentions": [],
        "urls": [],
        "created_at": None
    }

def extract_hashtags(text: str) -> List[str]:
    """Extract hashtags from tweet text"""
    pattern = r'#(\w+)'
    return re.findall(pattern, text)

def extract_mentions(text: str) -> List[str]:
    """Extract mentions from tweet text"""
    pattern = r'@(\w+)'
    return re.findall(pattern, text)

def extract_urls(text: str) -> List[str]:
    """Extract URLs from tweet text"""
    pattern = r'https?://[^\s]+'
    return re.findall(pattern, text)

def parse_tweet_json(data: Dict) -> Dict:
    """Parse tweet from JSON (Twitter API format)"""
    return {
        "id": data.get("id_str", data.get("id")),
        "text": data.get("text", data.get("full_text", "")),
        "author_username": data.get("user", {}).get("screen_name"),
        "author_id": data.get("user", {}).get("id_str"),
        "hashtags": [h["text"] for h in data.get("entities", {}).get("hashtags", [])],
        "mentions": [m["screen_name"] for m in data.get("entities", {}).get("user_mentions", [])],
        "urls": [u["expanded_url"] for u in data.get("entities", {}).get("urls", [])],
        "created_at": parse_twitter_date(data.get("created_at")),
        "reply_to": data.get("in_reply_to_status_id_str"),
        "quote_of": data.get("quoted_status_id_str")
    }

def parse_twitter_date(date_str: str) -> Optional[datetime]:
    """Parse Twitter date format"""
    if not date_str:
        return None
    try:
        # Twitter format: "Wed Oct 10 20:19:24 +0000 2018"
        return datetime.strptime(date_str, "%a %b %d %H:%M:%S %z %Y")
    except:
        return None
