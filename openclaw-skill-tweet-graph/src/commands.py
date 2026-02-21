# Commands for Tweet Graph Skill

from .skill import (
    store_tweet_from_url, store_tweet_manual,
    search_tweets, get_related, get_stats,
    format_search_results, format_related_results
)
from .url_parser import is_twitter_url

async def handle_store_command(args: str) -> str:
    """Handle: store this tweet: [url or data]"""
    args = args.strip()
    
    # Check if it's a URL
    if is_twitter_url(args):
        result = await store_tweet_from_url(args)
        if result["success"]:
            data = result["data"]
            return f"✅ Tweet stored!\n- ID: {data['id']}\n- Status: {data['message']}"
        else:
            return f"❌ Failed to store: {result['error']}"
    
    # Otherwise, parse as manual entry
    # Format: "id: xxx, text: xxx, author: xxx"
    lines = args.split("\n")
    data = {}
    for line in lines:
        if ":" in line:
            key, value = line.split(":", 1)
            data[key.strip()] = value.strip()
    
    if "id" not in data or "text" not in data:
        return "❌ Manual tweet needs 'id:' and 'text:' fields"
    
    result = await store_tweet_manual(data)
    if result["success"]:
        return f"✅ Tweet stored: {result['data']['id']}"
    else:
        return f"❌ Failed: {result['error']}"

async def handle_search_command(args: str) -> str:
    """Handle: find tweets about: [query]"""
    query = args.strip()
    if not query:
        return "Usage: find tweets about: [query]"
    
    result = await search_tweets(query)
    if result["success"]:
        data = result["data"]
        return f"Found {data['count']} tweets:\n{format_search_results(data['results'])}"
    else:
        return f"❌ Search failed: {result['error']}"

async def handle_related_command(args: str) -> str:
    """Handle: show related to tweet: [id]"""
    tweet_id = args.strip()
    if not tweet_id:
        return "Usage: show related to tweet: [tweet_id]"
    
    result = await get_related(tweet_id)
    if result["success"]:
        data = result["data"]
        return f"Related nodes ({data['count']}):\n{format_related_results(data['related'])}"
    else:
        return f"❌ Query failed: {result['error']}"

async def handle_stats_command() -> str:
    """Handle: tweet graph stats"""
    result = await get_stats()
    if result["success"]:
        stats = result["data"]
        return (
            f"📊 Tweet Graph Statistics:\n"
            f"- Tweets: {stats.get('tweets', 0)}\n"
            f"- Users: {stats.get('users', 0)}\n"
            f"- Hashtags: {stats.get('hashtags', 0)}\n"
            f"- Relationships: {stats.get('relationships', 0)}"
        )
    else:
        return f"❌ Stats failed: {result['error']}"

# Command registry
COMMANDS = {
    "store this tweet": handle_store_command,
    "store tweet": handle_store_command,
    "find tweets about": handle_search_command,
    "search for tweets about": handle_search_command,
    "show related to tweet": handle_related_command,
    "what's connected to": handle_related_command,
    "tweet graph stats": lambda _: handle_stats_command(),
}

async def process_command(text: str) -> str:
    """Process incoming text and route to appropriate handler"""
    text_lower = text.lower().strip()
    
    for cmd_prefix, handler in COMMANDS.items():
        if text_lower.startswith(cmd_prefix):
            args = text[len(cmd_prefix):].strip()
            return await handler(args)
    
    return None  # No command matched
