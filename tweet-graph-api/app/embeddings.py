# Embeddings - Multi-provider support

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
    
    payload = {
        "input": text,
        "model": model
    }
    
    # Some providers support dimensions parameter
    if dimensions and "openai" in api_base:
        payload["dimensions"] = dimensions
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                headers=headers,
                json=payload,
                timeout=30.0
            )
            
            if response.status_code != 200:
                logger.error(f"Embedding API error: {response.status_code} - {response.text}")
                return [0.0] * dimensions
            
            data = response.json()
            
            # Handle different response formats
            if "data" in data and len(data["data"]) > 0:
                return data["data"][0]["embedding"]
            elif "embedding" in data:
                return data["embedding"]
            else:
                logger.error(f"Unexpected response format: {data}")
                return [0.0] * dimensions
                
    except Exception as e:
        logger.error(f"Embedding request failed: {e}")
        return [0.0] * dimensions

async def get_embeddings_batch(texts: List[str], config: dict) -> List[List[float]]:
    """
    Generate embeddings for multiple texts in batch
    
    Args:
        texts: List of texts to embed
        config: Provider configuration
    
    Returns:
        List of embedding vectors
    """
    # For efficiency, batch requests if provider supports it
    # Otherwise, fall back to individual requests
    
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
    
    payload = {
        "input": texts,
        "model": model
    }
    
    if dimensions and "openai" in api_base:
        payload["dimensions"] = dimensions
    
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
                # Sort by index to maintain order
                embeddings = sorted(data["data"], key=lambda x: x.get("index", 0))
                return [e["embedding"] for e in embeddings]
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
        "nomic-embed-text": 768,
        "nomic-embed-text-v1": 768,
        "all-MiniLM-L6-v2": 384,
    }
    
    for key, dims in dimension_map.items():
        if key in model.lower():
            return dims
    
    return 1536  # Default
