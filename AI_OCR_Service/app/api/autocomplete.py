from fastapi import APIRouter, Query, HTTPException
from typing import List, Any
from app.core.config.config import settings
from app.services.search.search_indexer import es_service
from app.core.logging.logger import get_logger
from app.core.logging.async_logger import log_performance

logger = get_logger(__name__)
router = APIRouter(tags=["Search: Discovery"])

def extract_suggestions(data: Any) -> List[str]:
    """Recursively extract string values from nested ES field structures."""
    suggestions = []
    if isinstance(data, list):
        for item in data:
            suggestions.extend(extract_suggestions(item))
    elif isinstance(data, dict):
        for value in data.values():
            suggestions.extend(extract_suggestions(value))
    elif isinstance(data, (str, int, float)):
        suggestions.append(str(data))
    return suggestions

@router.get("/autocomplete")
@log_performance("Search: Autocomplete")
async def autocomplete(
    q: str = Query(..., min_length=2, description="Partial search term"),
    user_id: str = Query(..., description="User ID for isolation"),
    size: int = Query(5, ge=1, le=20)
):
    """
    Real-time autocomplete suggestions for medicines, doctors, and hospitals.
    
    Returns a deduplicated list of strings.
    """
    try:
        # Build V8 lightweight query
        from app.services.search.search_indexer import QueryBuilder
        body = QueryBuilder.build_autocomplete_search(q, user_id, size)
        
        # Execute search with circuit breaker / timeout protection
        client = es_service.get_async_client()
        if not client:
            return []
            
        response = await client.search(
            index=settings.ES_INDEX_ALIAS,
            body=body,
            request_timeout=2
        )
        
        raw_suggestions = []
        hits = response.get("hits", {}).get("hits", [])
        
        for hit in hits:
            fields = hit.get("fields", {})
            raw_suggestions.extend(extract_suggestions(fields))
        
        # Deduplicate and return
        return list(set(raw_suggestions))
        
    except Exception as e:
        logger.error(f"Autocomplete error: {e}")
        # Circuit breaker: Fallback to empty list instead of crashing
        return []
