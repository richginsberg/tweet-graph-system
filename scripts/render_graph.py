#!/usr/bin/env python3
"""
Generate graph visualization with optional tweet screenshot cards
"""

import sys
import json
import requests
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, Circle
from matplotlib.offsetbox import OffsetImage, AnnotationBbox
import networkx as nx
from io import BytesIO
import textwrap
from pathlib import Path
from PIL import Image
import numpy as np
import subprocess

API_URL = "http://localhost:8000"
DEBUG_LOG = "/tmp/tweet-graph-skill.log"

def debug_log(msg):
    """Log debug messages"""
    import datetime
    with open(DEBUG_LOG, "a") as f:
        f.write(f"[{datetime.datetime.now()}] {msg}\n")
        f.flush()

# Screenshots directory - uses XDG_DATA_HOME or falls back to ~/.local/share
SCREENSHOT_DIR = Path.home() / ".local" / "share" / "tweet-graph" / "screenshots"

def get_accessible_ip():
    """Get Tailscale IP if available, otherwise LAN IP"""
    try:
        result = subprocess.run(['tailscale', 'ip'], capture_output=True, text=True, timeout=2)
        if result.returncode == 0:
            return result.stdout.strip().split('\n')[0]  # First IP (IPv4)
    except:
        pass
    
    # Fallback to LAN IP
    try:
        result = subprocess.run(['hostname', '-I'], capture_output=True, text=True)
        ips = result.stdout.strip().split()
        if ips:
            return ips[0]
    except:
        pass
    
    return "localhost"

NODE_COLORS = {
    "Tweet": "#1DA1F2",
    "User": "#8b5cf6", 
    "Hashtag": "#22c55e",
    "Theme": "#f59e0b",
    "Entity": "#ef4444",
    "URL": "#6366f1",
}

EDGE_COLORS = {
    "POSTED": "#8b5cf6",
    "HAS_HASHTAG": "#22c55e",
    "MENTIONS": "#8b5cf6",
    "ABOUT_THEME": "#f59e0b",
    "MENTIONS_ENTITY": "#ef4444",
    "CONTAINS_URL": "#6366f1",
}

def get_graph_data(filter_query: str = None):
    if filter_query:
        search_resp = requests.post(f"{API_URL}/search", json={"query": filter_query, "limit": 10})
        if search_resp.ok:
            results = search_resp.json().get("results", [])
            search_tweet_ids = set(r["id"] for r in results)
            resp = requests.get(f"{API_URL}/graph")
            if resp.ok:
                data = resp.json()
                
                # Build mapping from tweet ID (in node.name) to sequential node ID
                tweet_id_to_seq = {}
                for node in data["nodes"]:
                    if node["type"] == "Tweet":
                        # For Tweet nodes, name contains the tweet ID
                        tweet_id_to_seq[node["name"]] = node["id"]
                
                # Convert search tweet IDs to sequential IDs
                seq_ids = set()
                for tid in search_tweet_ids:
                    if tid in tweet_id_to_seq:
                        seq_ids.add(tweet_id_to_seq[tid])
                
                related_ids = set(seq_ids)
                filtered_nodes = []
                filtered_links = []
                
                # Filter links that connect to our search results
                for link in data["links"]:
                    if link["source"] in seq_ids or link["target"] in seq_ids:
                        filtered_links.append(link)
                        related_ids.add(link["source"])
                        related_ids.add(link["target"])
                
                # Filter nodes that are in our related set
                for node in data["nodes"]:
                    if node["id"] in related_ids:
                        filtered_nodes.append(node)
                
                return {"nodes": filtered_nodes, "links": filtered_links}
    else:
        resp = requests.get(f"{API_URL}/graph")
        if resp.ok:
            return resp.json()
    return {"nodes": [], "links": []}

def get_stats():
    resp = requests.get(f"{API_URL}/stats")
    return resp.json() if resp.ok else {}

def get_tweets():
    resp = requests.get(f"{API_URL}/tweets")
    return resp.json() if resp.ok else []

def load_screenshot(tweet_id: str):
    """Load screenshot if available"""
    path = SCREENSHOT_DIR / f"{tweet_id}.png"
    if path.exists():
        return Image.open(path)
    return None

def render_graph(filter_query: str = None, output_path: str = None, use_screenshots: bool = True) -> bytes:
    data = get_graph_data(filter_query)
    stats = get_stats()
    tweets = get_tweets()
    tweet_map = {t["id"]: t for t in tweets}
    
    if not data["nodes"]:
        fig, ax = plt.subplots(figsize=(12, 8))
        ax.text(0.5, 0.5, "No tweets in graph\n\nRun /sync to fetch bookmarks", 
                ha='center', va='center', fontsize=18, color='#888', weight='bold')
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.axis('off')
        ax.set_facecolor('#0d1117')
        fig.patch.set_facecolor('#0d1117')
    else:
        G = nx.DiGraph()
        node_data = {}
        
        for node in data["nodes"]:
            G.add_node(node["id"], type=node["type"], name=node.get("name", ""))
            node_data[node["id"]] = node
        
        edge_types = {}
        for link in data["links"]:
            G.add_edge(link["source"], link["target"], type=link.get("type", "RELATED"))
            edge_types[(link["source"], link["target"])] = link.get("type", "RELATED")
        
        fig, ax = plt.subplots(figsize=(18, 14))
        ax.set_facecolor('#0d1117')
        fig.patch.set_facecolor('#0d1117')
        
        pos = nx.spring_layout(G, k=4, iterations=200, seed=42, scale=3)
        
        # Draw edges
        for (source, target), rel_type in edge_types.items():
            color = EDGE_COLORS.get(rel_type, "#444")
            style = 'dashed' if rel_type in ['ABOUT_THEME', 'MENTIONS_ENTITY'] else 'solid'
            nx.draw_networkx_edges(G, pos, edgelist=[(source, target)], 
                                  ax=ax, edge_color=color, width=2, alpha=0.6,
                                  arrows=True, arrowsize=20,
                                  style=style,
                                  connectionstyle="arc3,rad=0.15")
        
        # Draw nodes
        for node_id in G.nodes():
            node = node_data[node_id]
            x, y = pos[node_id]
            node_type = node["type"]
            color = NODE_COLORS.get(node_type, "#666")
            
            if node_type == "Tweet":
                tweet = tweet_map.get(node_id, {})
                author = tweet.get("author", "unknown")
                text = tweet.get("text", "")[:80]
                
                # Try to load screenshot
                screenshot = load_screenshot(node_id) if use_screenshots else None
                
                if screenshot:
                    # Show screenshot as card
                    img_array = np.array(screenshot.resize((200, 150)))
                    imagebox = OffsetImage(img_array, zoom=0.8)
                    ab = AnnotationBbox(imagebox, (x, y), frameon=True,
                                       bboxprops=dict(boxstyle="round,pad=0.02",
                                                     facecolor='#16181c', 
                                                     edgecolor=color,
                                                     linewidth=2))
                    ax.add_artist(ab)
                else:
                    # Show text card
                    card_w, card_h = 1.0, 0.5
                    rect = FancyBboxPatch((x - card_w/2, y - card_h/2), 
                                         card_w, card_h,
                                         boxstyle="round,pad=0.02,rounding_size=0.08",
                                         facecolor='#16181c', edgecolor=color, linewidth=2)
                    ax.add_patch(rect)
                    
                    ax.text(x, y + 0.15, f"@{author}", fontsize=10, fontweight='bold',
                           color='white', ha='center', va='center')
                    
                    wrapped = textwrap.fill(text, width=30)
                    ax.text(x, y - 0.08, wrapped, fontsize=7, color='#8899a6',
                           ha='center', va='center')
            
            elif node_type == "User":
                circle = Circle((x, y), 0.2, color=color, alpha=0.8)
                ax.add_patch(circle)
                ax.text(x, y, f"@{node['name'][:8]}", fontsize=9, color='white',
                       ha='center', va='center', fontweight='bold')
            
            elif node_type == "Hashtag":
                rect = FancyBboxPatch((x - 0.25, y - 0.12), 0.5, 0.24,
                                     boxstyle="round,pad=0.02",
                                     facecolor=color, edgecolor='none', alpha=0.8)
                ax.add_patch(rect)
                ax.text(x, y, f"#{node['name'][:10]}", fontsize=9, color='white',
                       ha='center', va='center', fontweight='bold')
            
            elif node_type == "Theme":
                diamond = plt.Polygon([(x, y+0.18), (x+0.18, y), (x, y-0.18), (x-0.18, y)],
                                     color=color, alpha=0.8)
                ax.add_patch(diamond)
                ax.text(x, y-0.3, node['name'], fontsize=8, color=color, ha='center')
            
            else:
                circle = Circle((x, y), 0.12, color=color, alpha=0.7)
                ax.add_patch(circle)
                ax.text(x, y-0.2, node['name'][:12], fontsize=7, color=color, ha='center')
        
        # Legends
        node_patches = [mpatches.Patch(color=c, label=t, alpha=0.8) 
                       for t, c in list(NODE_COLORS.items())[:5]]
        ax.legend(handles=node_patches, loc='upper left',
                 facecolor='#16181c', edgecolor='#333', labelcolor='white', fontsize=9)
        
        edge_patches = [mpatches.Patch(color=c, label=t.replace('_', ' ').title(), alpha=0.8)
                       for t, c in list(EDGE_COLORS.items())[:5]]
        ax.legend(handles=edge_patches, loc='upper right',
                 facecolor='#16181c', edgecolor='#333', labelcolor='white', fontsize=9)
        
        # Stats
        accessible_ip = get_accessible_ip()
        portal_url = f"http://{accessible_ip}:3000/graph"
        stats_text = f"{stats.get('tweets', 0)} tweets | {stats.get('users', 0)} users | {len(data['nodes'])} nodes | {len(data['links'])} edges"
        if filter_query:
            stats_text = f"Query: '{filter_query}' | {stats_text}"
        fig.text(0.5, 0.02, stats_text, ha='center', fontsize=11, color='#8899a6')
        fig.text(0.5, 0.005, f"Portal: {portal_url}", ha='center', fontsize=10, color='#1DA1F2', weight='bold')
        
        ax.axis('off')
        ax.set_xlim(-4, 4)
        ax.set_ylim(-3.5, 3.5)
        plt.tight_layout()
    
    buf = BytesIO()
    plt.savefig(buf, format='png', dpi=150, bbox_inches='tight',
                facecolor=fig.get_facecolor())
    buf.seek(0)
    plt.close(fig)
    
    if output_path:
        with open(output_path, 'wb') as f:
            f.write(buf.getvalue())
    
    return buf.getvalue()

def main():
    query = sys.argv[1] if len(sys.argv) > 1 and sys.argv[1] != "None" else None
    output = sys.argv[2] if len(sys.argv) > 2 else "/tmp/tweet-graph.png"
    
    print(f"Generating graph{' for: ' + query if query else ''}...")
    img_data = render_graph(query, output)
    print(f"Saved to: {output}")
    print(f"Size: {len(img_data)} bytes")

if __name__ == "__main__":
    main()
