"""
Semantic Reranker

Reranks search results using cross-encoder models for better relevance.
Provides semantic similarity scoring for search result refinement.
"""

import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from app.core.logging.logger import get_logger  # type: ignore[import]

logger = get_logger("reranker")


@dataclass
class RerankedResult:
    """Result with reranking score."""
    original_hit: Dict[str, Any]
    score: float
    rank: int


class SemanticReranker:
    """
    Reranks search results using semantic similarity.
    Uses cross-encoder or bi-encoder models for scoring.
    """
    
    def __init__(self, model_name: Optional[str] = None):
        self._model = None
        self._model_name = model_name or "cross-encoder/ms-marco-MiniLM-L-6-v2"
        self._initialize()
    
    def _initialize(self):
        """Initialize the reranker model."""
        try:
            from sentence_transformers import CrossEncoder  # type: ignore[import]
            
            self._model = CrossEncoder(self._model_name)
            logger.info(f"✅ Reranker initialized with {self._model_name}")
        except ImportError:
            logger.warning("⚠️ sentence-transformers not available, using fallback reranking")
        except Exception as e:
            logger.error(f"❌ Failed to initialize reranker: {e}")
    
    def rerank(
        self,
        query: str,
        candidates: List[Dict[str, Any]],
        top_k: int = 10,
        text_field: str = "raw_text"
    ) -> List[Dict[str, Any]]:
        """
        Rerank candidates based on semantic similarity to query.
        
        Args:
            query: Original search query
            candidates: List of candidate documents from ES
            top_k: Number of top results to return
            text_field: Field containing text to compare
        
        Returns:
            Reranked list of candidates
        """
        if not candidates:
            return []
        
        if self._model is None:
            # Fallback: return original order
            logger.debug("No reranker model, returning original order")
            return candidates[:top_k]  # type: ignore[index]
        
        try:
            # Prepare pairs for scoring
            pairs = []
            valid_candidates = []
            
            for candidate in candidates:
                text = self._extract_text(candidate, text_field)
                if text:
                    pairs.append([query, text])
                    valid_candidates.append(candidate)
            
            if not pairs:
                return candidates[:top_k]  # type: ignore[index]
            
            # Score all pairs
            scores = self._model.predict(pairs)  # type: ignore[union-attr]
            
            # Combine candidates with scores
            reranked = [
                RerankedResult(original_hit=candidate, score=float(score), rank=i)
                for i, (candidate, score) in enumerate(zip(valid_candidates, scores))
            ]
            
            # Sort by score (descending)
            reranked.sort(key=lambda x: x.score, reverse=True)
            
            # Return top_k with metadata
            results = []
            for i, result in enumerate(reranked[:top_k], 1):  # type: ignore[index]
                hit = result.original_hit.copy()
                hit["_rerank_score"] = round(result.score, 4)
                hit["_rerank_position"] = i
                results.append(hit)
            
            logger.debug(f"Reranked {len(candidates)} candidates to {len(results)} results")
            return results
            
        except Exception as e:
            logger.error(f"Reranking failed: {e}")
            return candidates[:top_k]  # type: ignore[index]
    
    def _extract_text(self, candidate: Dict[str, Any], field: str) -> str:
        """Extract text from candidate document."""
        if "_source" in candidate:
            source = candidate["_source"]
            if field in source:
                return str(source[field])
            
            # Try alternative fields
            for alt_field in ["medicine_names", "doctor_name", "hospital", "diagnosis"]:
                if alt_field in source:
                    return str(source[alt_field])
        
        elif field in candidate:
            return str(candidate[field])
        
        return ""


# Global reranker instance
_reranker: Optional[SemanticReranker] = None


def get_reranker() -> SemanticReranker:
    """Get or create the semantic reranker."""
    global _reranker
    if _reranker is None:
        _reranker = SemanticReranker()
    return _reranker


# Convenience alias
reranker = get_reranker()