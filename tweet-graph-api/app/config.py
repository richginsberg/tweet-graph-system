# Configuration - Multi-provider support

from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # Neo4j
    NEO4J_URI: str = "bolt://neo4j:7687"
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: str = "tweetgraph123"
    
    # X/Twitter API (for enrichment)
    TWITTER_BEARER_TOKEN: str = ""
    TWITTER_API_TIER: str = "free"  # free, basic, pro
    
    # Embedding Provider (OpenAI-compatible)
    EMBEDDING_PROVIDER: str = "openai"  # openai, deepseek, together, groq, ollama, local
    EMBEDDING_API_KEY: str = ""
    EMBEDDING_API_BASE: str = ""  # Leave empty for default provider
    EMBEDDING_MODEL: str = "text-embedding-3-small"
    EMBEDDING_DIMENSIONS: int = 1536
    
    # Legacy support (maps to EMBEDDING_API_KEY)
    OPENAI_API_KEY: str = ""
    
    class Config:
        env_file = ".env"
    
    def get_embedding_config(self) -> dict:
        """Get embedding configuration based on provider"""
        api_key = self.EMBEDDING_API_KEY or self.OPENAI_API_KEY
        
        # Provider-specific defaults
        provider_configs = {
            "openai": {
                "api_base": "https://api.openai.com/v1",
                "model": "text-embedding-3-small",
                "dimensions": 1536
            },
            "deepinfra": {
                "api_base": "https://api.deepinfra.com/v1/openai/embeddings",
                "model": "BAAI/bge-base-en-v1.5",
                "dimensions": 768
            },
            "chutes-8b": {
                "api_base": "https://chutes-qwen-qwen3-embedding-8b.chutes.ai/v1",
                "model": "qwen3-embedding-8b",
                "dimensions": 4096
            },
            "chutes-0.6b": {
                "api_base": "https://chutes-qwen-qwen3-embedding-0-6b.chutes.ai/v1",
                "model": "qwen3-embedding-0.6b",
                "dimensions": 1024
            },
            "deepseek": {
                "api_base": "https://api.deepseek.com/v1",
                "model": "deepseek-embed",
                "dimensions": 1536
            },
            "together": {
                "api_base": "https://api.together.xyz/v1",
                "model": "togethercomputer/m2-bert-80M-8k-retrieval",
                "dimensions": 768
            },
            "groq": {
                "api_base": "https://api.groq.com/openai/v1",
                "model": "nomic-embed-text-v1",
                "dimensions": 768
            },
            "ollama": {
                "api_base": "http://localhost:11434/v1",
                "model": "nomic-embed-text",
                "dimensions": 768
            },
            "local": {
                "api_base": "http://localhost:8000/v1",
                "model": "local-embedding",
                "dimensions": 1536
            },
            "custom": {
                "api_base": self.EMBEDDING_API_BASE,
                "model": self.EMBEDDING_MODEL,
                "dimensions": self.EMBEDDING_DIMENSIONS
            }
        }
        
        config = provider_configs.get(self.EMBEDDING_PROVIDER, provider_configs["openai"])
        
        # Override with user settings if provided
        if self.EMBEDDING_API_BASE:
            config["api_base"] = self.EMBEDDING_API_BASE
        if self.EMBEDDING_MODEL:
            config["model"] = self.EMBEDDING_MODEL
        if self.EMBEDDING_DIMENSIONS:
            config["dimensions"] = self.EMBEDDING_DIMENSIONS
        
        config["api_key"] = api_key
        return config

settings = Settings()
