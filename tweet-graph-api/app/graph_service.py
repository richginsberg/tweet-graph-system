# Graph Service - Core business logic

from app.neo4j_client import Neo4jClient
from app.models import TweetCreate
from app.embeddings import get_embedding
import logging

logger = logging.getLogger(__name__)

class GraphService:
    def __init__(self, client: Neo4jClient, embedding_config: dict):
        self.client = client
        self.embedding_config = embedding_config
        self.dimensions = embedding_config.get("dimensions", 1536)
    
    async def init_vector_index(self):
        """Create vector index for tweet embeddings"""
        query = f"""
        CREATE VECTOR INDEX tweet_embedding IF NOT EXISTS
        FOR (t:Tweet)
        ON t.embedding
        OPTIONS {{
            indexConfig: {{
                `vector.dimensions`: {self.dimensions},
                `vector.similarity_function`: 'cosine'
            }}
        }}
        """
        try:
            await self.client.execute(query)
            logger.info(f"Vector index created with {self.dimensions} dimensions")
        except Exception as e:
            logger.warning(f"Vector index may already exist: {e}")
    
    async def store_tweet(self, tweet: TweetCreate) -> dict:
        """Store tweet with all relationships"""
        
        # Generate embedding using configured provider
        embedding = await get_embedding(tweet.text, self.embedding_config)
        
        query = """
        MERGE (t:Tweet {id: $id})
        SET t.text = $text,
            t.created_at = $created_at,
            t.bookmark_url = $bookmark_url,
            t.embedding = $embedding
        
        // Create author
        WITH t
        OPTIONAL MATCH (u:User {id: $author_id})
        FOREACH (_ IN CASE WHEN $author_id IS NOT NULL THEN [1] ELSE [] END |
            MERGE (author:User {id: $author_id})
            SET author.username = $author_username
            MERGE (author)-[:POSTED]->(t)
        )
        
        // Create hashtags
        WITH t
        UNWIND $hashtags AS tag
        MERGE (h:Hashtag {tag: tag})
        MERGE (t)-[:HAS_HASHTAG]->(h)
        
        // Create mentions
        WITH t
        UNWIND $mentions AS mention
        MERGE (m:User {username: mention})
        MERGE (t)-[:MENTIONS]->(m)
        
        // Create URLs
        WITH t
        UNWIND $urls AS url
        MERGE (u:URL {url: url})
        MERGE (t)-[:CONTAINS_URL]->(u)
        
        // Create reply relationship
        WITH t
        OPTIONAL MATCH (reply_to:Tweet {id: $reply_to})
        FOREACH (_ IN CASE WHEN $reply_to IS NOT NULL THEN [1] ELSE [] END |
            MERGE (t)-[:REPLY_TO]->(reply_to)
        )
        
        // Create quote relationship
        WITH t
        OPTIONAL MATCH (quote_of:Tweet {id: $quote_of})
        FOREACH (_ IN CASE WHEN $quote_of IS NOT NULL THEN [1] ELSE [] END |
            MERGE (t)-[:QUOTES]->(quote_of)
        )
        
        RETURN t.id as id
        """
        
        result = await self.client.execute_single(query, {
            "id": tweet.id,
            "text": tweet.text,
            "created_at": tweet.created_at.isoformat() if tweet.created_at else None,
            "bookmark_url": tweet.bookmark_url,
            "embedding": embedding,
            "author_id": tweet.author_id,
            "author_username": tweet.author_username,
            "hashtags": tweet.hashtags or [],
            "mentions": tweet.mentions or [],
            "urls": tweet.urls or [],
            "reply_to": tweet.reply_to,
            "quote_of": tweet.quote_of
        })
        
        return result or {"id": tweet.id}
    
    async def get_tweet(self, tweet_id: str) -> dict:
        """Get tweet by ID"""
        query = """
        MATCH (t:Tweet {id: $id})
        OPTIONAL MATCH (u:User)-[:POSTED]->(t)
        RETURN t.id as id, t.text as text, t.created_at as created_at,
               u.username as author,
               [(t)-[:HAS_HASHTAG]->(h) | h.tag] as hashtags,
               [(t)-[:MENTIONS]->(m) | m.username] as mentions
        """
        return await self.client.execute_single(query, {"id": tweet_id})
    
    async def vector_search(self, query: str, limit: int = 10) -> list:
        """Vector similarity search"""
        embedding = await get_embedding(query, self.embedding_config)
        
        cypher = """
        CALL db.index.vector.queryNodes('tweet_embedding', $limit, $embedding)
        YIELD node AS t, score
        OPTIONAL MATCH (u:User)-[:POSTED]->(t)
        RETURN t.id as id, t.text as text, 
               u.username as author,
               score,
               [(t)-[:HAS_HASHTAG]->(h) | h.tag] as hashtags
        ORDER BY score DESC
        """
        
        results = await self.client.execute(cypher, {
            "embedding": embedding,
            "limit": limit
        })
        
        return results
    
    async def get_related(self, tweet_id: str, depth: int = 2, 
                         relationship_types: list = None) -> list:
        """Get related nodes via graph traversal"""
        
        rel_pattern = "|".join(relationship_types) if relationship_types else "POSTED|HAS_HASHTAG|MENTIONS|REPLY_TO|QUOTES|CONTAINS_URL"
        
        query = f"""
        MATCH (t:Tweet {{id: $id}})
        MATCH (t)-[r:{rel_pattern}*1..{depth}]-(related)
        RETURN DISTINCT
            labels(related)[0] as type,
            related.id as id,
            properties(related) as properties,
            type(last(r)) as relationship
        LIMIT 50
        """
        
        return await self.client.execute(query, {"id": tweet_id})
    
    async def get_stats(self) -> dict:
        """Get database statistics"""
        queries = {
            "tweets": "MATCH (t:Tweet) RETURN count(t) as count",
            "users": "MATCH (u:User) RETURN count(u) as count",
            "hashtags": "MATCH (h:Hashtag) RETURN count(h) as count",
            "relationships": "MATCH ()-[r]->() RETURN count(r) as count"
        }
        
        stats = {}
        for key, query in queries.items():
            result = await self.client.execute_single(query)
            stats[key] = result["count"] if result else 0
        
        return stats
