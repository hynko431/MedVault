"""
Embeddings Service

Provides text embedding generation for semantic search.
Supports multiple embedding providers with fallback.
"""

import hashlib
import logging
from typing import List, Optional, Dict, Any
from functools import lru_cache

from app.core.config.config import settings  # type: ignore[import]
from app.core.logging.logger import get_logger  # type: ignore[import]
from app.core.storage.cache import cached  # type: ignore[import]

logger = get_logger("embeddings")


class EmbeddingService:
    """
    Service for generating text embeddings.
    Supports multiple providers with fallback chain.
    """
    
    _provider: Optional[Any] = None  # may be str sentinel OR SentenceTransformer
    _model_name: Optional[str] = None

    def __init__(self):
        self._provider = None
        self._model_name = None
        self._initialize()
    
    def _initialize(self):
        """Initialize the embedding service with available provider."""
        # Try providers in order of preference
        providers = [
            self._init_sentence_transformers,
            self._init_openai,
            self._init_jina,
        ]
        
        for provider_init in providers:
            try:
                if provider_init():
                    logger.info(f"✅ Embedding service initialized with {self._model_name}")
                    return
            except Exception as e:
                logger.warning(f"⚠️ Failed to initialize embedding provider: {e}")
                continue
        
        logger.error("❌ No embedding provider available")
    
    def _init_sentence_transformers(self) -> bool:
        """Initialize sentence-transformers embedding."""
        try:
            from sentence_transformers import SentenceTransformer  # type: ignore[import]
            
            # Use a lightweight model suitable for medical text
            model_name = getattr(settings, 'EMBEDDING_MODEL', 'sentence-transformers/all-MiniLM-L6-v2')
            self._provider = SentenceTransformer(model_name)
            self._model_name = model_name
            return True
        except ImportError:
            return False
    
    def _init_openai(self) -> bool:
        """Initialize OpenAI embedding."""
        if not getattr(settings, 'OPENAI_API_KEY', None):
            return False
        
        try:
            import openai  # type: ignore[import]
            openai.api_key = getattr(settings, 'OPENAI_API_KEY', '')
            self._provider = "openai"
            self._model_name = "text-embedding-3-small"
            return True
        except ImportError:
            return False
    
    def _init_jina(self) -> bool:
        """Initialize Jina AI embedding."""
        if not getattr(settings, 'JINA_API_KEY', None):
            return False
        
        try:
            self._provider = "jina"
            self._model_name = "jina-embeddings-v2-base-en"
            return True
        except Exception:
            return False
    
    def embed_query(self, text: str) -> List[float]:
        """
        Generate embedding for a query text.
        
        Args:
            text: The text to embed
        
        Returns:
            Embedding vector as list of floats
        """
        if not text:
            # Return zero vector for empty text
            return [0.0] * self._get_dimensions()
        
        try:
            if self._provider is None:
                raise RuntimeError("No embedding provider available")
            
            if hasattr(self._provider, 'encode'):
                # SentenceTransformers
                embedding = self._provider.encode(text, convert_to_numpy=True)  # type: ignore[union-attr]
                return embedding.tolist()  # type: ignore[union-attr]
            
            elif self._provider == "openai":
                # OpenAI API
                import openai  # type: ignore[import]
                response = openai.embeddings.create(
                    model=self._model_name or "text-embedding-3-small",
                    input=text
                )
                return response.data[0].embedding
            elif self._provider == "jina":
                # Jina AI API
                import httpx  # type: ignore[import]
                response = httpx.post(
                    "https://api.jina.ai/v1/embeddings",
                    headers={"Authorization": f"Bearer {settings.JINA_API_KEY}"},  # type: ignore
                    json={
                        "model": self._model_name or "jina-embeddings-v2-base-en",
                        "input": [text]
                    }
                )
                response.raise_for_status()
                return response.json()["data"][0]["embedding"]
            
            else:
                raise RuntimeError(f"Unknown embedding provider: {self._provider}")
        
        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            # Return zero vector as fallback
            return [0.0] * self._get_dimensions()
    
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple documents.
        
        Args:
            texts: List of texts to embed
        
        Returns:
            List of embedding vectors
        """
        if not texts:
            return []
        
        try:
            if self._provider is None:
                raise RuntimeError("No embedding provider available")
            
            if hasattr(self._provider, 'encode'):
                # SentenceTransformers (batch processing)
                embeddings = self._provider.encode(texts, convert_to_numpy=True, show_progress_bar=False)  # type: ignore[union-attr]
                return [emb.tolist() for emb in embeddings]  # type: ignore[union-attr]
            
            else:
                # For API-based providers, process individually
                return [self.embed_query(text) for text in texts]
        
        except Exception as e:
            logger.error(f"Failed to batch embed documents: {e}")
            # Return zero vectors as fallback
            return [[0.0] * self._get_dimensions() for _ in texts]
    
    def _get_dimensions(self) -> int:
        """Get the embedding dimensions for the current model."""
        dimensions = {
            'sentence-transformers/all-MiniLM-L6-v2': 384,
            'sentence-transformers/all-mpnet-base-v2': 768,
            'text-embedding-3-small': 1536,
            'text-embedding-3-large': 3072,
            'jina-embeddings-v2-base-en': 768,
        }
        return dimensions.get(self._model_name or "", 768)  # Default to 768
    
    def similarity(self, emb1: List[float], emb2: List[float]) -> float:
        """
        Calculate cosine similarity between two embeddings.
        
        Args:
            emb1: First embedding vector
            emb2: Second embedding vector
        
        Returns:
            Cosine similarity score (0-1)
        """
        import numpy as np  # type: ignore[import]
        
        v1 = np.array(emb1)
        v2 = np.array(emb2)
        
        dot_product = np.dot(v1, v2)
        norm1 = np.linalg.norm(v1)
        norm2 = np.linalg.norm(v2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return float(dot_product / (norm1 * norm2))


# Global embedding service instance
_embedding_service: Optional[EmbeddingService] = None


def get_embedding_service() -> EmbeddingService:
    """Get or create the embedding service."""
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService()
    return _embedding_service


# Convenience alias for backward compatibility
embedding_service = get_embedding_service()