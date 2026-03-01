# Theme and Entity Extraction

import re
import logging
from typing import List, Set, Tuple, Optional
from app.ner_providers import get_ner_provider, NERProvider

logger = logging.getLogger(__name__)

# Global NER provider instance (lazy-loaded)
_ner_provider: Optional[NERProvider] = None


def init_ner_provider(provider: str = "regex", **kwargs):
    """Initialize the global NER provider"""
    global _ner_provider
    _ner_provider = get_ner_provider(provider, **kwargs)
    logger.info(f"Initialized NER provider: {_ner_provider.name}")


def get_ner() -> NERProvider:
    """Get the current NER provider (initializes with regex if not set)"""
    global _ner_provider
    if _ner_provider is None:
        _ner_provider = get_ner_provider("regex")
    return _ner_provider


def extract_themes(text: str) -> List[str]:
    """
    Extract themes from tweet text using keyword matching
    
    This is fast and reliable for common tech/business topics.
    No ML model required.
    """
    text_lower = text.lower()
    
    # Common AI/tech/business themes with keywords
    theme_keywords = {
        "ai": ["ai", "artificial intelligence", "machine learning", "ml", "deep learning", "neural network"],
        "llm": ["llm", "gpt", "chatgpt", "claude", "openai", "anthropic", "gemini", "llama", "qwen", "deepseek"],
        "agents": ["agent", "agentic", "autonomous", "automation", "workflow", "copilot"],
        "infrastructure": ["cloud", "aws", "gcp", "azure", "kubernetes", "docker", "api", "serverless"],
        "business": ["startup", "b2b", "b2c", "saas", "enterprise", "founder", "vc", "funding", "revenue"],
        "crypto": ["blockchain", "crypto", "bitcoin", "ethereum", "defi", "nft", "web3", "solana"],
        "dev": ["python", "javascript", "typescript", "rust", "golang", "coding", "programming", "github"],
        "security": ["security", "privacy", "encryption", "auth", "authentication", "cybersecurity"],
        "hardware": ["gpu", "cpu", "nvidia", "amd", "chip", "semiconductor", "hardware"],
        "research": ["paper", "arxiv", "study", "research", "benchmark", "experiment"],
    }
    
    themes = set()
    for theme_category, keywords in theme_keywords.items():
        for keyword in keywords:
            if keyword in text_lower:
                themes.add(theme_category)
                break  # Only add theme once per category
    
    return list(themes)


def extract_entities(text: str) -> List[str]:
    """
    Extract named entities from text using configured NER provider
    
    Provider is configured via NER_PROVIDER environment variable.
    Falls back to regex if provider fails.
    """
    ner = get_ner()
    try:
        return ner.extract_entities(text)
    except Exception as e:
        logger.error(f"NER extraction failed: {e}")
        return []


def extract_themes_and_entities(text: str) -> Tuple[List[str], List[str]]:
    """
    Extract themes and entities from tweet text
    
    Returns:
        (themes, entities)
    """
    themes = extract_themes(text)
    entities = extract_entities(text)
    
    return themes, entities
