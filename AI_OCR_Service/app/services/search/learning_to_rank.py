"""
Learning to Rank (LTR) Service

Collects search interactions for training ranking models.
Provides logging and data collection for improving search relevance over time.
"""

import json
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
from pathlib import Path

from app.core.config.config import settings
from app.core.logging.logger import get_logger

logger = get_logger("ltr_service")


class LTRService:
    """
    Learning to Rank service for collecting search interaction data.
    Logs queries, results, and user interactions to build training datasets.
    """
    
    def __init__(self, log_file: Optional[str] = None):
        self._log_file = log_file or "logs/search_interactions.jsonl"
        self._ensure_log_directory()
    
    def _ensure_log_directory(self):
        """Ensure log directory exists."""
        try:
            Path(self._log_file).parent.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            logger.warning(f"Could not create log directory: {e}")
    
    def log_interaction(
        self,
        user_id: str,
        query: str,
        prescription_id: str,
        rank_position: int,
        features: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Log a search interaction event.
        
        Args:
            user_id: User who performed the search
            query: The search query
            prescription_id: ID of the clicked result
            rank_position: Position of the clicked result
            features: Optional features about the result
        
        Returns:
            True if logged successfully
        """
        try:
            interaction = {
                "timestamp": datetime.utcnow().isoformat(),
                "user_id": user_id,
                "query": query,
                "prescription_id": prescription_id,
                "rank_position": rank_position,
                "features": features or {},
                "event_type": "click",
            }
            
            # Append to log file
            with open(self._log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(interaction, ensure_ascii=False) + "\n")
            
            logger.debug(f"Logged interaction: query='{query}', position={rank_position}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to log interaction: {e}")
            return False
    
    def log_search(
        self,
        user_id: str,
        query: str,
        results_count: int,
        intent: Optional[str] = None,
        latency_ms: Optional[float] = None
    ) -> bool:
        """
        Log a search query event.
        
        Args:
            user_id: User who performed the search
            query: The search query
            results_count: Number of results returned
            intent: Detected search intent
            latency_ms: Search latency in milliseconds
        
        Returns:
            True if logged successfully
        """
        try:
            search_event = {
                "timestamp": datetime.utcnow().isoformat(),
                "user_id": user_id,
                "query": query,
                "results_count": results_count,
                "intent": intent,
                "latency_ms": latency_ms,
                "event_type": "search",
            }
            
            with open(self._log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(search_event, ensure_ascii=False) + "\n")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to log search: {e}")
            return False
    
    def get_interactions(
        self,
        user_id: Optional[str] = None,
        query: Optional[str] = None,
        limit: int = 1000
    ) -> List[Dict[str, Any]]:
        """
        Retrieve logged interactions for analysis.
        
        Args:
            user_id: Filter by user
            query: Filter by query
            limit: Maximum number of interactions to retrieve
        
        Returns:
            List of interaction records
        """
        interactions = []
        
        try:
            if not Path(self._log_file).exists():
                return interactions
            
            with open(self._log_file, "r", encoding="utf-8") as f:
                for line in f:
                    if len(interactions) >= limit:
                        break
                    
                    try:
                        interaction = json.loads(line.strip())
                        
                        # Apply filters
                        if user_id and interaction.get("user_id") != user_id:
                            continue
                        if query and interaction.get("query") != query:
                            continue
                        
                        interactions.append(interaction)
                        
                    except json.JSONDecodeError:
                        continue
            
            return interactions
            
        except Exception as e:
            logger.error(f"Failed to read interactions: {e}")
            return []
    
    def get_popular_queries(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get most popular search queries.
        
        Args:
            limit: Maximum number of queries to return
        
        Returns:
            List of popular queries with counts
        """
        from collections import Counter
        
        try:
            queries = []
            
            if not Path(self._log_file).exists():
                return []
            
            with open(self._log_file, "r", encoding="utf-8") as f:
                for line in f:
                    try:
                        interaction = json.loads(line.strip())
                        if interaction.get("event_type") == "search":
                            queries.append(interaction.get("query", ""))
                    except json.JSONDecodeError:
                        continue
            
            # Count and return top queries
            counter = Counter(q for q in queries if q)
            return [
                {"query": query, "count": count}
                for query, count in counter.most_common(limit)
            ]
            
        except Exception as e:
            logger.error(f"Failed to get popular queries: {e}")
            return []


# Global LTR service instance
_ltr_service: Optional[LTRService] = None


def get_ltr_service() -> LTRService:
    """Get or create the LTR service."""
    global _ltr_service
    if _ltr_service is None:
        _ltr_service = LTRService()
    return _ltr_service


# Convenience alias
ltr_service = get_ltr_service()