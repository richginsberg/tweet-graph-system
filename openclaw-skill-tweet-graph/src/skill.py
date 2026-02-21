# Tweet Graph Skill - Main Module

import re
import httpx
from typing import Optional, Dict, List, Any

TWEET_GRAPH_API_URL = "http://tweet-graph-api:8000"

def extract_tweet_id(url: str) -> Optional[str]:
    """Extract tweet ID from Twitter/X URL"""
    patterns = [
        r'twitter\.com/\w+/status/(\d+)',
        r'x\.com/\w+/status/(\d+)',
        r'twitter\.com/\w+/statuses/(\d+)',
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None

async def store_tweet_from_url(url: str) -> Dict[str, Any]:
    """Store a tweet from its URL"""
    tweet_id = extract_tweet_id(url)
    if not tweet_id:
        return {"success": False, "error": "Invalid tweet URL"}
    
    # For now, store with URL as bookmark
    # In production, would fetch actual tweet data via API
    tweet_data = {
        "id": tweet_id,
        "text": f"Tweet from {url}",
        "bookmark_url": url,
        "author_id": None,
        "author_username": None
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{TWEET_GRAPH_API_URL}/tweets",
            json=tweet_data,
            timeout=30.0
        )
        
        if response.status_code == 200:
            return {"success": True, "data": response.json()}
        else:
            return {"success": False, "error": response.text}

async def store_tweet_manual(data: Dict[str, Any]) -> Dict[str, Any]:
    """Store a manually entered tweet"""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{TWEET_GRAPH_API_URL}/tweets",
            json=data,
            timeout=30.0
        )
        
        if response.status_code == 200:
            return {"success": True, "data": response.json()}
        else:
            return {"success": False, "error": response.text}

async def search_tweets(query: str, limit: int = 10) -> Dict[str, Any]:
    """Search for tweets using vector similarity"""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{TWEET_GRAPH_API_URL}/search",
            json={"query": query, "limit": limit},
            timeout=30.0
        )
        
        if response.status_code == 200:
            return {"success": True, "data": response.json()}
        else:
            return {"success": False, "error": response.text}

async def get_related(tweet_id: str, depth: int = 2) -> Dict[str, Any]:
    """Get related nodes for a tweet"""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{TWEET_GRAPH_API_URL}/related",
            json={"tweet_id": tweet_id, "depth": depth},
            timeout=30.0
        )
        
        if response.status_code == 200:
            return {"success": True, "data": response.json()}
        else:
            return {"success": False, "error": response.text}

async def get_stats() -> Dict[str, Any]:
    """Get graph statistics"""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{TWEET_GRAPH_API_URL}/stats",
            timeout=10.0
        )
        
        if response.status_code == 200:
            return {"success": True, "data": response.json()}
        else:
            return {"success": False, "error": response.text}

def format_tweet_display(tweet: Dict[str, Any]) -> str:
    """Format tweet for display"""
    text = tweet.get("text", "")[:200]
    author = tweet.get("author", "unknown")
    hashtags = tweet.get("hashtags", [])
    
    output = f"📝 @{author}: {text}"
    if hashtags:
        output += f"\n🏷️ {', '.join(['#' + h for h in hashtags])}"
    
    return output

def format_search_results(results: List[Dict]) -> str:
    """Format search results for display"""
    if not results:
        return "No tweets found."
    
    output = []
    for i, result in enumerate(results, 1):
        score = result.get("score", 0)
        text = result.get("text", "")[:100]
        author = result.get("author", "unknown")
        output.append(f"{i}. [Score: {score:.2f}] @{author}: {text}")
    
    return "\n".join(output)

def format_related_results(results: List[Dict]) -> str:
    """Format related nodes for display"""
    if not results:
        return "No related nodes found."
    
    output = []
    for node in results:
        node_type = node.get("type", "Unknown")
        rel = node.get("relationship", "unknown")
        props = node.get("properties", {})
        
        if node_type == "Hashtag":
            output.append(f"🏷️ #{props.get('tag', 'unknown')} ({rel})")
        elif node_type == "User":
            output.append(f"👤 @{props.get('username', 'unknown')} ({rel})")
        elif node_type == "Tweet":
            text = props.get("text", "")[:50]
            output.append(f"📝 {text}... ({rel})")
        else:
            output.append(f"📦 {node_type}: {props}")
    
    return "\n".join(output)
