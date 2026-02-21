# Theme and Entity Extraction

import re
from typing import List, Set, Tuple

def extract_themes_and_entities(text: str) -> Tuple[List[str], List[str]]:
    """
    Extract themes and proper nouns from tweet text
    
    Returns:
        (themes, entities)
    """
    text_lower = text.lower()
    
    # Common AI/tech/business themes
    theme_keywords = {
        "ai": ["ai", "artificial intelligence", "machine learning", "ml", "deep learning", "neural network"],
        "llm": ["llm", "gpt", "chatgpt", "claude", "openai", "anthropic", "gemini", "llama"],
        "agents": ["agent", "agentic", "autonomous", "automation", "workflow"],
        "infrastructure": ["cloud", "aws", "gcp", "azure", "kubernetes", "docker", "api"],
        "business": ["startup", "b2b", "b2c", "saas", "enterprise", "founder", "vc", "funding"],
        "crypto": ["blockchain", "crypto", "bitcoin", "ethereum", "defi", "nft", "web3"],
        "dev": ["python", "javascript", "typescript", "rust", "go", "coding", "programming"],
        "security": ["security", "privacy", "encryption", "auth", "authentication"]
    }
    
    themes = set()
    for theme_category, keywords in theme_keywords.items():
        for keyword in keywords:
            if keyword in text_lower:
                themes.add(theme_category)
                break
    
    # Extract proper nouns (capitalized words not at sentence start)
    entities = set()
    
    # Multi-word proper nouns (e.g., "Elon Musk", "Sam Altman")
    multi_word = re.findall(r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\b', text)
    entities.update(multi_word)
    
    # Company/product names (capitalized words)
    sentences = re.split(r'[.!?]+\s+', text)
    for i, sentence in enumerate(sentences):
        words = sentence.split()
        for j, word in enumerate(words):
            # Skip first word of first sentence (usually capitalized)
            if i == 0 and j == 0:
                continue
            # Skip common words
            if word.lower() in {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'}:
                continue
            # Check if proper noun
            if word and word[0].isupper() and len(word) > 1:
                clean = re.sub(r'[^a-zA-Z0-9]', '', word)
                if len(clean) > 2:
                    entities.add(clean)
    
    return list(themes), list(entities)
