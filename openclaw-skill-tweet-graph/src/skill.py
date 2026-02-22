# Tweet Graph Skill - Main Module

import os
import re
import httpx
from typing import Optional, Dict, List, Any

# API URL - can be overridden via environment
TWEET_GRAPH_API_URL = os.environ.get("TWEET_GRAPH_API_URL", "http://localhost:8000")

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

async def get_all_tweets() -> Dict[str, Any]:
    """Get all tweets"""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{TWEET_GRAPH_API_URL}/tweets",
            timeout=30.0
        )
        
        if response.status_code == 200:
            return {"success": True, "data": response.json()}
        else:
            return {"success": False, "error": response.text}

async def get_themes() -> Dict[str, Any]:
    """Get all themes with counts"""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{TWEET_GRAPH_API_URL}/themes",
            timeout=10.0
        )
        
        if response.status_code == 200:
            return {"success": True, "data": response.json()}
        else:
            return {"success": False, "error": response.text}

async def get_entities() -> Dict[str, Any]:
    """Get all entities with counts"""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{TWEET_GRAPH_API_URL}/entities",
            timeout=10.0
        )
        
        if response.status_code == 200:
            return {"success": True, "data": response.json()}
        else:
            return {"success": False, "error": response.text}

async def sync_bookmarks(bookmarks: List[Dict]) -> Dict[str, Any]:
    """Sync bookmarks to the graph"""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{TWEET_GRAPH_API_URL}/bookmarks/sync",
            json={"bookmarks": bookmarks},
            timeout=120.0
        )
        
        if response.status_code == 200:
            return {"success": True, "data": response.json()}
        else:
            return {"success": False, "error": response.text}

# Formatting functions

def format_tweet_display(tweet: Dict[str, Any]) -> str:
    """Format tweet for display with themes and entities"""
    text = tweet.get("text", "")[:200]
    author = tweet.get("author", "unknown")
    hashtags = tweet.get("hashtags", [])
    themes = tweet.get("themes", [])
    truncated = tweet.get("truncated", False)
    
    output = f"📝 @{author}"
    if truncated:
        output += " 📖"
    output += f": {text}"
    
    if hashtags:
        output += f"\n🏷️ {', '.join(['#' + h for h in hashtags])}"
    
    if themes:
        output += f"\n🎯 Themes: {', '.join(themes)}"
    
    return output

def format_search_results(results: List[Dict]) -> str:
    """Format search results with similarity scores and themes"""
    if not results:
        return "No tweets found."
    
    output = []
    for i, result in enumerate(results, 1):
        score = result.get("score", 0)
        score_pct = int(score * 100)
        text = result.get("text", "")[:100]
        author = result.get("author", "unknown")
        themes = result.get("themes", [])
        
        line = f"{i}. [{score_pct}%] @{author}: {text}"
        if themes:
            line += f"\n   🎯 {', '.join(themes)}"
        output.append(line)
    
    return "\n\n".join(output)

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
        elif node_type == "Theme":
            output.append(f"🎯 {props.get('name', 'unknown')} ({rel})")
        elif node_type == "Entity":
            output.append(f"📌 {props.get('name', 'unknown')} ({rel})")
        elif node_type == "Tweet":
            text = props.get("text", "")[:50]
            output.append(f"📝 {text}... ({rel})")
        else:
            output.append(f"📦 {node_type}: {props}")
    
    return "\n".join(output)

def format_stats(stats: Dict[str, Any]) -> str:
    """Format stats for display"""
    tweets = stats.get("tweets", 0)
    users = stats.get("users", 0)
    hashtags = stats.get("hashtags", 0)
    relationships = stats.get("relationships", 0)
    provider = stats.get("embedding_provider", "unknown")
    model = stats.get("embedding_model", "unknown")
    
    return f"""📊 **Tweet Graph Stats**

📝 Tweets: {tweets}
👤 Users: {users}
#️⃣ Hashtags: {hashtags}
🔗 Relationships: {relationships}

🤖 Embeddings: {provider}/{model}

🌐 Portal: http://localhost:3000
📡 API: http://localhost:8000"""

def format_themes(data: Dict[str, Any]) -> str:
    """Format themes for display"""
    themes = data.get("themes", [])
    if not themes:
        return "No themes found."
    
    output = ["🎯 **Themes in Your Tweets**\n"]
    for theme in themes:
        name = theme.get("name", "unknown")
        count = theme.get("count", 0)
        output.append(f"- **{name}**: {count} tweets")
    
    return "\n".join(output)

def format_entities(data: Dict[str, Any]) -> str:
    """Format entities for display"""
    entities = data.get("entities", [])
    if not entities:
        return "No entities found."
    
    output = ["📌 **Entities Detected**\n"]
    for entity in entities[:20]:  # Limit to top 20
        name = entity.get("name", "unknown")
        count = entity.get("count", 0)
        output.append(f"- **{name}**: {count} mentions")
    
    if len(entities) > 20:
        output.append(f"\n_...and {len(entities) - 20} more_")
    
    return "\n".join(output)

def format_sync_result(data: Dict[str, Any]) -> str:
    """Format sync result for display"""
    total = data.get("total_received", 0)
    new = data.get("new_stored", 0)
    updated = data.get("updated", 0)
    enriched = data.get("enriched", 0)
    duplicates = data.get("duplicates_skipped", 0)
    
    return f"""✅ **Bookmark Sync Complete**

📥 Total received: {total}
✨ New stored: {new}
🔄 Updated: {updated}
🔍 Enriched: {enriched}
📋 Duplicates: {duplicates}"""
