# Embeddings - Multi-provider support with better error handling

import httpx
import logging
from typing import List, Optional

logger = logging.getLogger(__name__)

async def get_embedding(text: str, config: dict) -> List[float]:
    """
    Generate embedding using OpenAI-compatible API
    
    Args:
        text: Text to embed
        config: Dict with api_key, api_base, model, dimensions
    
    Returns:
        List of floats (embedding vector)
    """
    api_key = config.get("api_key", "")
    api_base = config.get("api_base", "https://api.openai.com/v1")
    model = config.get("model", "text-embedding-3-small")
    dimensions = config.get("dimensions", 1536)
    
    if not api_key:
        logger.warning("No API key provided, returning zero vector")
        return [0.0] * dimensions
    
    # Prepare request
    url = f"{api_base.rstrip('/')}/embeddings"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    # Build payload - some providers (like Chutes) don't need model param
    payload = {"input": text}
    
    # Only include model if it's not null/empty and provider expects it
    if model and "chutes" not in api_base.lower():
        payload["model"] = model
    
    # Some providers support dimensions parameter
    if dimensions and "openai" in api_base:
        payload["dimensions"] = dimensions
    
    logger.info(f"Calling embedding API: {url}")
    logger.debug(f"Payload: {payload}")
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                headers=headers,
                json=payload,
                timeout=30.0
            )
            
            logger.info(f"Embedding API response status: {response.status_code}")
            
            if response.status_code != 200:
                logger.error(f"Embedding API error: {response.status_code} - {response.text}")
                return [0.0] * dimensions
            
            data = response.json()
            logger.debug(f"Response keys: {data.keys() if isinstance(data, dict) else 'not dict'}")
            
            # Handle different response formats
            if "data" in data and len(data["data"]) > 0:
                # OpenAI standard format
                return data["data"][0]["embedding"]
            elif "embedding" in data:
                # Some providers return embedding directly
                return data["embedding"]
            elif "embeddings" in data:
                # Alternative format
                return data["embeddings"][0] if isinstance(data["embeddings"], list) else data["embeddings"]
            else:
                logger.error(f"Unexpected response format: {list(data.keys())}")
                return [0.0] * dimensions
                
    except Exception as e:
        logger.error(f"Embedding request failed: {e}")
        return [0.0] * dimensions

async def get_embeddings_batch(texts: List[str], config: dict) -> List[List[float]]:
    """
    Generate embeddings for multiple texts in batch
    """
    api_key = config.get("api_key", "")
    api_base = config.get("api_base", "https://api.openai.com/v1")
    model = config.get("model", "text-embedding-3-small")
    dimensions = config.get("dimensions", 1536)
    
    if not api_key:
        return [[0.0] * dimensions for _ in texts]
    
    url = f"{api_base.rstrip('/')}/embeddings"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    payload = {"input": texts}
    if model and "chutes" not in api_base.lower():
        payload["model"] = model
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                headers=headers,
                json=payload,
                timeout=60.0
            )
            
            if response.status_code != 200:
                logger.error(f"Batch embedding failed: {response.text}")
                return [[0.0] * dimensions for _ in texts]
            
            data = response.json()
            
            if "data" in data:
                embeddings = sorted(data["data"], key=lambda x: x.get("index", 0))
                return [e["embedding"] for e in embeddings]
            elif "embeddings" in data:
                return data["embeddings"]
            else:
                return [[0.0] * dimensions for _ in texts]
                
    except Exception as e:
        logger.error(f"Batch embedding error: {e}")
        return [[0.0] * dimensions for _ in texts]

def estimate_dimensions(model: str) -> int:
    """Estimate embedding dimensions based on model name"""
    dimension_map = {
        "text-embedding-3-small": 1536,
        "text-embedding-3-large": 3072,
        "text-embedding-ada-002": 1536,
        "deepseek-embed": 1536,
        "qwen3-embedding-8b": 4096,
        "qwen3-embedding-0.6b": 1024,
        "nomic-embed-text": 768,
        "nomic-embed-text-v1": 768,
        "all-MiniLM-L6-v2": 384,
        "bge-base-en": 768,
    }
    
    for key, dims in dimension_map.items():
        if key in model.lower():
            return dims
    
    return 1536
