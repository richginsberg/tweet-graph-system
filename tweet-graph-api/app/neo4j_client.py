# Neo4j Client

from neo4j import AsyncGraphDatabase
import logging

logger = logging.getLogger(__name__)

class Neo4jClient:
    def __init__(self, uri: str, user: str, password: str):
        self.uri = uri
        self.user = user
        self.password = password
        self.driver = None
        self.connected = False
    
    async def connect(self):
        self.driver = AsyncGraphDatabase.driver(
            self.uri,
            auth=(self.user, self.password)
        )
        # Test connection
        async with self.driver.session() as session:
            await session.run("RETURN 1")
        self.connected = True
        logger.info(f"Connected to Neo4j at {self.uri}")
    
    async def close(self):
        if self.driver:
            await self.driver.close()
            self.connected = False
    
    async def execute(self, query: str, parameters: dict = None):
        async with self.driver.session() as session:
            result = await session.run(query, parameters or {})
            records = [record async for record in result]
            return [dict(record) for record in records]
    
    async def execute_single(self, query: str, parameters: dict = None):
        async with self.driver.session() as session:
            result = await session.run(query, parameters or {})
            record = await result.single()
            return dict(record) if record else None
    
    def session(self):
        """Get a Neo4j session context manager"""
        return self.driver.session()
