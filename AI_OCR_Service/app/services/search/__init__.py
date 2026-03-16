"""
Search Services Package

Provides search functionality with Elasticsearch:
- Search Indexer (indexing and querying)
- Embeddings (vector embeddings for semantic search)
- Intent Classifier (query intent detection)
- Reranker (semantic reranking)
- Learning to Rank (LTR data collection)

Example:
    >>> from app.services.search import search_indexer
    >>> from app.services.search.embeddings import embedding_service
    >>> from app.services.search.intent_classifier import get_intent_classifier
"""

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.services.search.search_indexer import es_service
    from app.services.search.embeddings import embedding_service

# Public API
__all__ = [
    "es_service",
    "embedding_service",
]


def __getattr__(name: str) -> Any:
    """
    Lazy attribute accessor for search services.
    """
    lazy_exports = {
        "search_indexer": "app.services.search.search_indexer",
        "embeddings": "app.services.search.embeddings",
        "intent_classifier": "app.services.search.intent_classifier",
        "reranker": "app.services.search.reranker",
        "learning_to_rank": "app.services.search.learning_to_rank",
        "es_service": "app.services.search.search_indexer",
        "embedding_service": "app.services.search.embeddings",
    }
    
    if name in lazy_exports:
        module_path = lazy_exports[name]
        import importlib
        module = importlib.import_module(module_path)
        return getattr(module, name, module)
    
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")