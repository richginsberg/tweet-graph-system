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
            t.embedding = $embedding,
            t.truncated = $truncated,
            t.author_username = $author_username
        
        // Create author relationship (by username or id)
        WITH t
        FOREACH (_ IN CASE WHEN $author_username IS NOT NULL AND $author_username <> '' THEN [1] ELSE [] END |
            MERGE (author:User {username: $author_username})
            MERGE (author)-[:POSTED]->(t)
        )
        FOREACH (_ IN CASE WHEN $author_id IS NOT NULL AND $author_id <> '' THEN [1] ELSE [] END |
            MERGE (author:User {id: $author_id})
            SET author.username = coalesce(author.username, $author_username)
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
            "truncated": tweet.truncated if tweet.truncated is not None else True,
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
    
    async def update_tweet_author(self, tweet_id: str, author_username: str):
        """Update tweet with author and create POSTED relationship"""
        query = """
        MATCH (t:Tweet {id: $id})
        SET t.author_username = $author
        WITH t
        MERGE (u:User {username: $author})
        MERGE (u)-[:POSTED]->(t)
        RETURN t.id as id
        """
        return await self.client.execute_single(query, {"id": tweet_id, "author": author_username})
    
    async def update_tweet_full_text(self, tweet_id: str, full_text: str, 
                                       hashtags: list = None, mentions: list = None,
                                       author_username: str = None):
        """Update tweet with full text from X API v2, set truncated=False"""
        # Update tweet properties
        query = """
        MATCH (t:Tweet {id: $id})
        SET t.text = $text, t.truncated = false
        """
        params = {"id": tweet_id, "text": full_text}
        
        await self.client.execute(query, params)
        
        # Update author if provided
        if author_username:
            await self.update_tweet_author(tweet_id, author_username)
        
        # Create hashtag relationships
        if hashtags:
            async with self.client.session() as session:
                for tag in hashtags:
                    await session.run("""
                        MATCH (t:Tweet {id: $id})
                        MERGE (h:Hashtag {tag: $tag})
                        MERGE (t)-[:HAS_HASHTAG]->(h)
                    """, id=tweet_id, tag=tag)
        
        # Create mention relationships
        if mentions:
            async with self.client.session() as session:
                for mention in mentions:
                    await session.run("""
                        MATCH (t:Tweet {id: $id})
                        MERGE (u:User {username: $mention})
                        MERGE (t)-[:MENTIONS]->(u)
                    """, id=tweet_id, mention=mention)
    
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
    
    async def get_graph_data(self) -> dict:
        """Get graph data for visualization"""
        async with self.client.session() as session:
            # Get all nodes with their types
            nodes_result = await session.run("""
                MATCH (n)
                RETURN id(n) as internal_id, labels(n)[0] as type, 
                       coalesce(n.id, n.name, n.tag, n.username, n.url, toString(id(n))) as name,
                       properties(n) as props
                LIMIT 500
            """)
            
            nodes = []
            node_id_map = {}
            
            async for record in nodes_result:
                internal_id = record["internal_id"]
                node_type = record["type"]
                name = record["name"] or "unknown"
                
                seq_id = str(len(nodes))
                node_id_map[internal_id] = seq_id
                
                nodes.append({
                    "id": seq_id,
                    "name": str(name),
                    "type": node_type,
                    "properties": dict(record["props"]) if record["props"] else {}
                })
            
            # Get all relationships
            links_result = await session.run("""
                MATCH (a)-[r]->(b)
                RETURN id(a) as source_id, id(b) as target_id, type(r) as rel_type
                LIMIT 1000
            """)
            
            links = []
            async for record in links_result:
                source_id = record["source_id"]
                target_id = record["target_id"]
                
                if source_id in node_id_map and target_id in node_id_map:
                    links.append({
                        "source": node_id_map[source_id],
                        "target": node_id_map[target_id],
                        "type": record["rel_type"]
                    })
            
            return {"nodes": nodes, "links": links}
    
    async def get_all_tweets(self) -> list:
        """Get all tweets with basic info"""
        async with self.client.session() as session:
            result = await session.run("""
                MATCH (t:Tweet)
                OPTIONAL MATCH (u:User)-[:POSTED]->(t)
                RETURN t.id as id, t.text as text, t.truncated as truncated,
                       coalesce(u.username, t.author_username) as author,
                       [(t)-[:HAS_HASHTAG]->(h) | h.tag] as hashtags,
                       [(t)-[:ABOUT_THEME]->(th) | th.name] as themes,
                       [(t)-[:MENTIONS_ENTITY]->(e) | e.name] as entities
                ORDER BY t.created_at DESC
                LIMIT 100
            """)
            
            tweets = []
            async for record in result:
                tweets.append({
                    "id": record["id"],
                    "text": record["text"],
                    "truncated": record["truncated"],
                    "author": record["author"],
                    "hashtags": record["hashtags"] or []
                })
            return tweets
    
    async def get_themes(self) -> dict:
        """Get all themes with tweet counts"""
        async with self.client.session() as session:
            result = await session.run("""
                MATCH (th:Theme)<-[:ABOUT_THEME]-(t:Tweet)
                RETURN th.name as name, count(t) as count
                ORDER BY count DESC
            """)
            
            themes = []
            async for record in result:
                themes.append({
                    "name": record["name"],
                    "count": record["count"]
                })
            return {"themes": themes}
    
    async def get_entities(self) -> dict:
        """Get all entities with mention counts"""
        async with self.client.session() as session:
            result = await session.run("""
                MATCH (e:Entity)<-[:MENTIONS_ENTITY]-(t:Tweet)
                RETURN e.name as name, count(t) as count
                ORDER BY count DESC
            """)
            
            entities = []
            async for record in result:
                entities.append({
                    "name": record["name"],
                    "count": record["count"]
                })
            return {"entities": entities}
