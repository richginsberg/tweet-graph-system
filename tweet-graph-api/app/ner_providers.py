# NER Providers - Pluggable Named Entity Recognition

import re
import logging
from typing import List, Tuple, Optional
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class NERProvider(ABC):
    """Base class for NER providers"""
    
    @abstractmethod
    def extract_entities(self, text: str) -> List[str]:
        """Extract named entities from text"""
        pass
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name"""
        pass


class RegexNERProvider(NERProvider):
    """
    Simple regex-based NER (fast but inaccurate)
    - Extracts capitalized words as potential entities
    - Many false positives (any capitalized word)
    - Good for: Quick processing, no dependencies
    - Bad for: Accuracy, noise in results
    """
    
    # Common English words to filter out (capitalized forms)
    COMMON_WORDS = {
        'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by',
        'this', 'that', 'these', 'those', 'it', 'its', 'is', 'was', 'are', 'were', 'be', 'been',
        'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may',
        'might', 'must', 'shall', 'can', 'need', 'dare', 'ought', 'used',
        'i', 'you', 'he', 'she', 'we', 'they', 'me', 'him', 'her', 'us', 'them',
        'my', 'your', 'his', 'her', 'its', 'our', 'their',
        'what', 'which', 'who', 'whom', 'whose', 'where', 'when', 'why', 'how',
        'here', 'there', 'now', 'then', 'just', 'only', 'also', 'even', 'still', 'already',
        'if', 'then', 'else', 'so', 'because', 'since', 'although', 'though', 'while',
        'some', 'any', 'no', 'none', 'all', 'both', 'each', 'every', 'either', 'neither',
        'one', 'two', 'three', 'first', 'second', 'third', 'last', 'next', 'other', 'another',
        'new', 'old', 'good', 'bad', 'best', 'worst', 'more', 'less', 'most', 'least',
        'very', 'too', 'quite', 'rather', 'pretty', 'really', 'actually', 'basically',
        'get', 'got', 'getting', 'go', 'going', 'gone', 'make', 'made', 'making',
        'take', 'took', 'taking', 'come', 'came', 'coming', 'see', 'saw', 'seeing',
        'know', 'knew', 'knowing', 'think', 'thought', 'thinking', 'want', 'wanted',
        'using', 'used', 'via', 'per', 'yet', 'heres', 'theres', 'thats', 'whats', 'im', 'ive',
        # Tech/common terms that aren't entities
        'api', 'sdk', 'ui', 'ux', 'ai', 'ml', 'llm', 'nlp', 'cpu', 'gpu', 'rss', 'http', 'https',
        'json', 'xml', 'html', 'css', 'sql', 'url', 'pdf', 'csv',
    }
    
    def __init__(self, min_length: int = 3):
        self.min_length = min_length
    
    @property
    def name(self) -> str:
        return "regex"
    
    def extract_entities(self, text: str) -> List[str]:
        entities = set()
        
        # Multi-word proper nouns (e.g., "Elon Musk", "Sam Altman")
        # Require both words to be capitalized and not common
        multi_word = re.findall(r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\b', text)
        for mw in multi_word:
            # Check if all parts are not common words
            parts = mw.lower().split()
            if not any(p in self.COMMON_WORDS for p in parts):
                entities.add(mw)
        
        # Single capitalized words (not at sentence start)
        sentences = re.split(r'[.!?]+\s+', text)
        for i, sentence in enumerate(sentences):
            words = sentence.split()
            for j, word in enumerate(words):
                # Skip first word of first sentence
                if i == 0 and j == 0:
                    continue
                
                # Clean the word
                clean = re.sub(r'[^a-zA-Z]', '', word)
                
                # Skip if empty or too short
                if len(clean) <= self.min_length:
                    continue
                
                # Skip if all lowercase
                if not clean[0].isupper():
                    continue
                
                # Skip common words
                if clean.lower() in self.COMMON_WORDS:
                    continue
                
                # Skip if it looks like a sentence starter (followed by verb)
                if j == 0 and i > 0:
                    continue
                
                entities.add(clean)
        
        return list(entities)


class SpacyNERProvider(NERProvider):
    """
    spaCy NER (fast and accurate)
    - Uses pre-trained models for entity recognition
    - Supports: PERSON, ORG, GPE, PRODUCT, EVENT, etc.
    - Models: en_core_web_sm (fast), en_core_web_lg (accurate)
    """
    
    def __init__(self, model: str = "en_core_web_sm"):
        self.model_name = model
        self._nlp = None
    
    @property
    def name(self) -> str:
        return f"spacy-{self.model_name}"
    
    def _load_model(self):
        if self._nlp is None:
            try:
                import spacy
                self._nlp = spacy.load(self.model_name)
                logger.info(f"Loaded spaCy model: {self.model_name}")
            except ImportError:
                logger.warning("spaCy not installed, falling back to regex")
                return None
            except OSError:
                logger.warning(f"spaCy model {self.model_name} not found, falling back to regex")
                return None
        return self._nlp
    
    def extract_entities(self, text: str) -> List[str]:
        nlp = self._load_model()
        if nlp is None:
            # Fallback to regex
            return RegexNERProvider().extract_entities(text)
        
        doc = nlp(text)
        entities = set()
        
        for ent in doc.ents:
            # Focus on: people, organizations, products, events
            if ent.label_ in ("PERSON", "ORG", "PRODUCT", "EVENT", "GPE", "LOC"):
                # Clean up entity text
                clean = ent.text.strip()
                if len(clean) > 2:
                    entities.add(clean)
        
        return list(entities)


class GLiNERProvider(NERProvider):
    """
    GLiNER NER (zero-shot capable)
    - Can extract any entity type via prompts
    - Slower than spaCy but more flexible
    - Models: small, medium, large
    """
    
    # Default entity types for tech/business tweets
    DEFAULT_LABELS = [
        "person",
        "organization", 
        "company",
        "product",
        "technology",
        "location",
        "event"
    ]
    
    def __init__(self, model: str = "urchade/gliner_small-v2.1", labels: List[str] = None):
        self.model_name = model
        self.labels = labels or self.DEFAULT_LABELS
        self._model = None
    
    @property
    def name(self) -> str:
        return f"gliner-{self.model_name.split('/')[-1]}"
    
    def _load_model(self):
        if self._model is None:
            try:
                from gliner import GLiNER
                self._model = GLiNER.from_pretrained(self.model_name)
                logger.info(f"Loaded GLiNER model: {self.model_name}")
            except ImportError:
                logger.warning("gliner not installed, falling back to regex")
                return None
            except Exception as e:
                logger.warning(f"Failed to load GLiNER: {e}, falling back to regex")
                return None
        return self._model
    
    def extract_entities(self, text: str) -> List[str]:
        model = self._load_model()
        if model is None:
            return RegexNERProvider().extract_entities(text)
        
        try:
            entities = model.predict_entities(text, self.labels, threshold=0.5)
            return list(set(e["text"] for e in entities if len(e["text"]) > 2))
        except Exception as e:
            logger.error(f"GLiNER extraction failed: {e}")
            return []


class MinibaseNERProvider(NERProvider):
    """
    Minibase NER (high recall)
    - 369MB model, 91.5% precision, 100% recall
    - Outputs: PER, ORG, LOC, MISC
    """
    
    def __init__(self, model: str = "Minibase/NER-Standard"):
        self.model_name = model
        self._pipeline = None
    
    @property
    def name(self) -> str:
        return f"minibase-{self.model_name.split('/')[-1]}"
    
    def _load_model(self):
        if self._pipeline is None:
            try:
                from transformers import pipeline
                self._pipeline = pipeline(
                    "token-classification",
                    model=self.model_name,
                    aggregation_strategy="simple"
                )
                logger.info(f"Loaded Minibase model: {self.model_name}")
            except ImportError:
                logger.warning("transformers not installed, falling back to regex")
                return None
            except Exception as e:
                logger.warning(f"Failed to load Minibase: {e}, falling back to regex")
                return None
        return self._pipeline
    
    def extract_entities(self, text: str) -> List[str]:
        pipeline = self._load_model()
        if pipeline is None:
            return RegexNERProvider().extract_entities(text)
        
        try:
            results = pipeline(text)
            entities = set()
            for ent in results:
                clean = ent["word"].strip()
                if len(clean) > 2:
                    entities.add(clean)
            return list(entities)
        except Exception as e:
            logger.error(f"Minibase extraction failed: {e}")
            return []


class DisabledNERProvider(NERProvider):
    """Disable entity extraction entirely"""
    
    @property
    def name(self) -> str:
        return "disabled"
    
    def extract_entities(self, text: str) -> List[str]:
        return []


def get_ner_provider(provider: str = "regex", **kwargs) -> NERProvider:
    """
    Get NER provider by name
    
    Args:
        provider: Provider name (regex, disabled, spacy-sm, spacy-lg, gliner, minibase)
        **kwargs: Additional arguments for provider
    
    Returns:
        NERProvider instance
    """
    providers = {
        "regex": RegexNERProvider,
        "disabled": DisabledNERProvider,
        "none": DisabledNERProvider,
    }
    
    # spaCy variants
    if provider.startswith("spacy"):
        if provider == "spacy" or provider == "spacy-sm":
            return SpacyNERProvider("en_core_web_sm", **kwargs)
        elif provider == "spacy-lg":
            return SpacyNERProvider("en_core_web_lg", **kwargs)
        elif provider == "spacy-trf":
            return SpacyNERProvider("en_core_web_trf", **kwargs)
        else:
            # Custom model name
            model = provider.replace("spacy-", "")
            return SpacyNERProvider(model, **kwargs)
    
    # GLiNER variants
    if provider.startswith("gliner"):
        if provider == "gliner" or provider == "gliner-small":
            return GLiNERProvider("urchade/gliner_small-v2.1", **kwargs)
        elif provider == "gliner-medium":
            return GLiNERProvider("urchade/gliner_medium-v2.1", **kwargs)
        elif provider == "gliner-large":
            return GLiNERProvider("urchade/gliner_large-v2.1", **kwargs)
        else:
            # Custom model
            model = provider.replace("gliner-", "urchade/gliner_") + "-v2.1"
            return GLiNERProvider(model, **kwargs)
    
    # Minibase
    if provider == "minibase":
        return MinibaseNERProvider(**kwargs)
    
    # Default to regex
    provider_class = providers.get(provider, RegexNERProvider)
    return provider_class(**kwargs)
