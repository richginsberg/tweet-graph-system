# Pydantic models for API

from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime

class TweetCreate(BaseModel):
    id: str
    text: str
    author_id: Optional[str] = None
    author_username: Optional[str] = None
    created_at: Optional[datetime] = None
    hashtags: Optional[List[str]] = []
    mentions: Optional[List[str]] = []
    urls: Optional[List[str]] = []
    reply_to: Optional[str] = None
    quote_of: Optional[str] = None
    bookmark_url: Optional[str] = None

class TweetResponse(BaseModel):
    id: str
    text: str
    stored: bool
    message: str
    related_count: Optional[int] = 0

class SearchRequest(BaseModel):
    query: str
    limit: int = 10

class SearchResult(BaseModel):
    id: str
    text: str
    author: Optional[str] = None
    score: float
    hashtags: List[str] = []

class SearchResponse(BaseModel):
    query: str
    results: List[SearchResult]
    count: int

class RelatedRequest(BaseModel):
    tweet_id: str
    depth: int = 2
    relationship_types: Optional[List[str]] = None

class RelatedNode(BaseModel):
    id: str
    type: str
    properties: Dict[str, Any]
    relationship: Optional[str] = None

class RelatedResponse(BaseModel):
    tweet_id: str
    related: List[RelatedNode]
    count: int

class BookmarkSyncRequest(BaseModel):
    bookmarks: List[Dict[str, Any]]
