# Commands for Tweet Graph Skill

from .skill import (
    store_tweet_from_url, store_tweet_manual,
    search_tweets, get_related, get_stats, get_all_tweets,
    get_themes, get_entities, sync_bookmarks,
    format_search_results, format_related_results,
    format_stats, format_themes, format_entities,
    format_sync_result
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
            return f"✅ Tweet stored!\n- ID: {data.get('id', 'unknown')}"
        else:
            return f"❌ Failed to store: {result['error']}"
    
    # Otherwise, parse as manual entry
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
        return f"✅ Tweet stored: {result['data'].get('id', 'unknown')}"
    else:
        return f"❌ Failed: {result['error']}"

async def handle_search_command(args: str) -> str:
    """Handle: find tweets about: [query] or /search [query]"""
    query = args.strip()
    if not query:
        return "Usage: find tweets about: [query] or /search [query]"
    
    result = await search_tweets(query)
    if result["success"]:
        data = result["data"]
        results = data.get("results", [])
        if not results:
            return f"No tweets found for: {query}"
        return f"Found {len(results)} tweets for \"{query}\":\n\n{format_search_results(results)}"
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
        related = data.get("related", [])
        return f"Related nodes ({len(related)}):\n{format_related_results(related)}"
    else:
        return f"❌ Query failed: {result['error']}"

async def handle_stats_command() -> str:
    """Handle: tweet graph stats or /stats"""
    result = await get_stats()
    if result["success"]:
        stats = result["data"]
        return format_stats(stats)
    else:
        return f"❌ Stats failed: {result['error']}"

async def handle_themes_command() -> str:
    """Handle: show themes or /themes"""
    result = await get_themes()
    if result["success"]:
        return format_themes(result["data"])
    else:
        return f"❌ Themes failed: {result['error']}"

async def handle_entities_command() -> str:
    """Handle: show entities or /entities"""
    result = await get_entities()
    if result["success"]:
        return format_entities(result["data"])
    else:
        return f"❌ Entities failed: {result['error']}"

async def handle_tweets_command() -> str:
    """Handle: /tweets - show recent tweets"""
    result = await get_all_tweets()
    if result["success"]:
        tweets = result["data"]
        if not tweets:
            return "No tweets in database. Run /sync to fetch bookmarks."
        
        output = [f"📝 **Latest Tweets** ({len(tweets)} total)\n"]
        for i, tweet in enumerate(tweets[:10], 1):
            author = tweet.get("author", "unknown")
            text = tweet.get("text", "")[:80]
            themes = tweet.get("themes", [])
            
            line = f"{i}. @{author}: {text}"
            if themes:
                line += f"\n   🎯 {', '.join(themes)}"
            output.append(line)
        
        if len(tweets) > 10:
            output.append(f"\n_...and {len(tweets) - 10} more_")
        
        return "\n\n".join(output)
    else:
        return f"❌ Failed: {result['error']}"

async def handle_sync_command() -> str:
    """Handle: /sync - sync X bookmarks"""
    # This would trigger the bookmark fetcher
    # For now, just return instructions
    return """🔄 **Sync X Bookmarks**

Run from terminal:
```bash
cd ~/.openclaw/workspace/tweet-graph-system/bookmark-fetcher
source venv/bin/activate
python -m fetcher.main_playwright
```

Or use hybrid mode (requires TWITTER_BEARER_TOKEN):
```bash
python -m fetcher.main_hybrid
```

Portal: http://localhost:3000"""

async def handle_graph_command() -> str:
    """Handle: /graph - show graph URL"""
    return """🕸️ **Tweet Graph Visualization**

Open in browser:
http://localhost:3000/graph

Interactive force-directed graph with:
- Tweets (blue)
- Users (purple)
- Hashtags (green)
- Themes (orange)
- Entities (red)"""

async def handle_help_command() -> str:
    """Handle: /help - show available commands"""
    return """📚 **Tweet Graph Commands**

**Short Commands:**
/tweets - Show latest tweets
/search <query> - Semantic search
/themes - Show themes
/stats - Database stats
/graph - Open visualization
/sync - Sync bookmarks

**Natural Language:**
"find tweets about: AI agents"
"search for tweets about: machine learning"
"store this tweet: https://x.com/..."
"show related to tweet: 123456"
"tweet graph stats"

**Portal:** http://localhost:3000"""

# Command registry - maps command prefixes to handlers
COMMANDS = {
    "store this tweet": handle_store_command,
    "store tweet": handle_store_command,
    "find tweets about": handle_search_command,
    "search for tweets about": handle_search_command,
    "show related to tweet": handle_related_command,
    "what's connected to": handle_related_command,
    "tweet graph stats": lambda _: handle_stats_command(),
    "show me themes": lambda _: handle_themes_command(),
    "show themes": lambda _: handle_themes_command(),
    "show entities": lambda _: handle_entities_command(),
    "open tweet graph": lambda _: handle_graph_command(),
}

# Short command registry - maps / commands to handlers
SHORT_COMMANDS = {
    "/tweets": handle_tweets_command,
    "/search": handle_search_command,
    "/themes": handle_themes_command,
    "/entities": handle_entities_command,
    "/stats": handle_stats_command,
    "/sync": handle_sync_command,
    "/graph": handle_graph_command,
    "/help": handle_help_command,
}

async def process_command(text: str) -> str:
    """Process incoming text and route to appropriate handler"""
    text_lower = text.lower().strip()
    
    # Check short commands first (e.g., /tweets, /search)
    for cmd_prefix, handler in SHORT_COMMANDS.items():
        if text_lower.startswith(cmd_prefix):
            args = text[len(cmd_prefix):].strip()
            return await handler(args)
    
    # Check natural language commands
    for cmd_prefix, handler in COMMANDS.items():
        if text_lower.startswith(cmd_prefix):
            args = text[len(cmd_prefix):].strip()
            return await handler(args)
    
    return None  # No command matched
