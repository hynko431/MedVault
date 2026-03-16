# 🌐 Search API Endpoints
from typing import List, Any, Dict, Optional
from fastapi import APIRouter, Query, HTTPException, Depends

from app.services.search.search_indexer import (
    search_by_medicine,
    search_by_doctor_or_hospital,
    search_all,
    search_with_date_range,
    autocomplete_search,
    fuzzy_search
)
from app.services.search.search_indexer import es_service, ElasticsearchClientFactory
from pydantic import BaseModel
from app.services.search.intent_classifier import get_intent_classifier, IntentClassifier, SearchIntent
from app.services.search.reranker import get_reranker, SemanticReranker
from app.services.search.learning_to_rank import get_ltr_service, LTRService
from app.core.config.config import settings
from app.core.db.elasticsearch import check_es_health, get_es
from app.core.storage.cache import cached
from app.services.search.embeddings import embedding_service
from app.core.logging.logger import get_logger
from app.core.logging.async_logger import log_performance

logger = get_logger(__name__)

router = APIRouter()


# Example endpoint demonstrating FastAPI dependency injection for Elasticsearch
@router.get("/direct-search", tags=["Search: Management"])
@log_performance("Search: Direct Search")
async def direct_es_search(
    q: str = Query(..., min_length=1, description="Search query"),
    user_id: str = Query(..., min_length=1, description="User ID"),
    size: int = Query(10, ge=1, le=100, description="Max results"),
    es: Any = Depends(get_es)
) -> Dict[str, Any]:
    """
    Example endpoint demonstrating direct Elasticsearch client usage via FastAPI dependency.
    
    This shows how to use the `get_es` dependency from `app.core.elasticsearch`
    to get an AsyncElasticsearch client in your route handlers.
    
    Usage:
        GET /search/direct-search?q=medicine&user_id=user123&size=10
    """
    try:
        # Build a simple search query
        body = {
            "size": size,
            "query": {
                "bool": {
                    "must": [
                        {
                            "multi_match": {
                                "query": q,
                                "fields": ["medicine_names^3", "doctor_name", "hospital", "raw_text"],
                                "fuzziness": "AUTO"
                            }
                        }
                    ],
                    "filter": [
                        {"term": {"user_id": user_id}}
                    ]
                }
            }
        }
        
        # Execute search using the injected ES client
        result = await es.search(
            index=settings.ES_INDEX,
            body=body
        )
        
        # Extract and return results
        hits = result.get("hits", {})
        total_info = hits.get("total", {})
        total_count = total_info.get("value", 0) if isinstance(total_info, dict) else total_info
        
        return {
            "total": total_count,
            "results": hits.get("hits", []),
            "query": q,
            "size": size
        }
        
    except Exception as e:
        logger.error(f"Direct ES search failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Search failed: {str(e)}"
        )


@router.get("/health-new", tags=["Search: Management"])
@log_performance("Search: Health New")
async def es_health_new() -> Dict[str, Any]:
    """
    Check Elasticsearch health using the new elasticsearch module.
    
    This demonstrates using the `check_es_health` function from 
    `app.core.elasticsearch`.
    """
    is_healthy = await check_es_health()
    
    return {
        "status": "healthy" if is_healthy else "unhealthy",
        "elasticsearch_host": settings.ES_HOST,
        "elasticsearch_enabled": settings.ELASTICSEARCH_ENABLED,
        "message": "Elasticsearch is connected and operational" if is_healthy else "Cannot connect to Elasticsearch"
    }


@router.get("/health", tags=["Search: Management"])
@log_performance("Search: Health Check")
async def search_health_check() -> Dict[str, Any]:
    """
    Check Elasticsearch search service health status.
    Returns detailed diagnostics about the search service.
    """
    health_status = {
        "status": "unknown",
        "elasticsearch_enabled": settings.ELASTICSEARCH_ENABLED,
        "elasticsearch_host": settings.ES_HOST,
        "elasticsearch_connected": False,
        "index_exists": False,
        "index_name": settings.ES_INDEX,
        "message": ""
    }
    
    if not settings.ELASTICSEARCH_ENABLED:
        health_status["status"] = "disabled"
        health_status["message"] = "Elasticsearch is disabled in configuration. Set ELASTICSEARCH_ENABLED=true in .env"
        return health_status
    
    # Test connection
    client = ElasticsearchClientFactory.get_async_client()
    if client is None:
        health_status["status"] = "error"
        health_status["message"] = "Failed to create Elasticsearch client"
        return health_status
    
    try:
        # Test ping
        ping_result = await client.ping()
        health_status["elasticsearch_connected"] = ping_result
        
        if not ping_result:
            health_status["status"] = "unavailable"
            health_status["message"] = f"Cannot connect to Elasticsearch at {settings.ES_HOST}. Ensure ES is running."
            return health_status
        
        # Get cluster health info
        cluster_health = await client.cluster.health()
        health_status["cluster_status"] = cluster_health.get("status")
        health_status["number_of_nodes"] = cluster_health.get("number_of_nodes")
        health_status["active_shards"] = cluster_health.get("active_shards")
        
        # Check index
        exists = await client.indices.exists(index=settings.ES_INDEX)
        # Convert HeadApiResponse to boolean (ES 8.x returns object, not bool)
        health_status["index_exists"] = bool(exists)
        
        health_status: Dict[str, Any] = {
            "status": "unknown",
            "message": "Initializing...",
            "document_count": 0
        }
        
        if not exists:
            health_status["status"] = "warning"
            health_status["message"] = f"Index '{settings.ES_INDEX}' does not exist. Run indexing to create it."
        else:
            health_status["status"] = "healthy"
            health_status["message"] = "Search service is operational"
            
            # Get index stats
            stats = await client.indices.stats(index=settings.ES_INDEX)
            doc_info = stats.get("_all", {}).get("primaries", {}).get("docs", {})
            health_status["document_count"] = int(doc_info.get("count", 0))
        
        return health_status
        
    except Exception as e:
        health_status["status"] = "error"
        health_status["message"] = f"Error checking health: {str(e)}"
        logger.error(f"Health check failed: {e}")
        return health_status


# Removed search_medicine_async as search_medicine is now also async and handles the same logic.


def _extract_hits(result: Any) -> List[Dict[str, Any]]:
    """
    Extract hits from Elasticsearch result, handling None and missing data.
    
    Args:
        result: Elasticsearch search result or None
    
    Returns:
        List of hit documents
    
    Raises:
        HTTPException: If Elasticsearch is unavailable (result is None)
    """
    if result is None:
        raise HTTPException(
            status_code=503,
            detail="Search service is currently unavailable"
        )
    
    # Handle both SearchResult object and dict (for backward compatibility)
    if hasattr(result, "hits"):
        return result.hits
    return result.get("hits", {}).get("hits", [])


def _extract_paginated_response(result: Any, page: int, page_size: int) -> Dict[str, Any]:
    """
    Extract paginated response from Elasticsearch result with proper error handling.
    
    Args:
        result: Elasticsearch search result or None
        page: Current page number
        page_size: Number of results per page
    
    Returns:
        Dictionary containing total count, pagination info, and results
    
    Raises:
        HTTPException: If Elasticsearch is unavailable or result structure is invalid
    """
    if result is None:
        raise HTTPException(
            status_code=503,
            detail="Search service is currently unavailable"
        )
    
    try:
        # Handle SearchResult object
        if hasattr(result, "total"):
            return {
                "total": result.total,
                "page": result.page,
                "page_size": result.page_size,
                "results": result.hits
            }
            
        # Handle dict format
        hits = result.get("hits", {})
        total_info = hits.get("total", {})
        
        # Handle both dict format {"value": n} and direct integer
        total_count = total_info.get("value", 0) if isinstance(total_info, dict) else total_info
        
        return {
            "total": total_count,
            "page": page,
            "page_size": page_size,
            "results": hits.get("hits", [])
        }
    except (AttributeError, KeyError, TypeError) as e:
        raise HTTPException(
            status_code=500,
            detail=f"Invalid search response structure: {str(e)}"
        )


# 🔍 2.1 Search by Medicine Endpoint
@router.get("/medicine", tags=["Search: Core"])
@log_performance("Search: By Medicine")
async def search_medicine(
    q: str = Query(..., description="Medicine name"),
    user_id: str = Query(..., description="User ID"),
    size: int = Query(10, ge=1, le=100, description="Max results to return")
) -> List[Dict[str, Any]]:
    """Search prescriptions by medicine name with fuzzy matching."""
    result = await search_by_medicine(q, user_id, size)
    return _extract_hits(result)


# 🔍 2.2 Search by Doctor / Hospital
@router.get("/provider", tags=["Search: Core"])
@log_performance("Search: By Provider")
async def search_provider(
    q: str = Query(..., description="Doctor name or hospital"),
    user_id: str = Query(..., description="User ID"),
    size: int = Query(10, ge=1, le=100, description="Max results to return")
) -> List[Dict[str, Any]]:
    """Search prescriptions by doctor name or hospital."""
    result = await search_by_doctor_or_hospital(q, user_id, size)
    return _extract_hits(result)


# 🔍 2.3 Universal Search (Recommended)
@router.get("/all", tags=["Search: Core"])
@router.get("/search", tags=["Search: Core"])  # Added alias for backward compatibility/legacy tests
@cached(ttl=120, key_prefix="search_everything")
@log_performance("Search: Universal")
async def search_everything(
    q: str = Query(..., description="Search text"),
    user_id: str = Query(..., description="User ID"),
    page: int = Query(1, ge=1, description="Page number (starts at 1)"),
    page_size: int = Query(10, ge=1, le=100, description="Results per page"),
    sort_by: str = Query("relevance", pattern="^(relevance|date)$", description="Sort by relevance or date")
) -> Dict[str, Any]:
    """
    Search prescriptions across all fields (medicine, doctor, hospital).
    Returns paginated results with total count and metadata.
    """
    result = await search_all(q, user_id, page, page_size, sort_by)
    return _extract_paginated_response(result, page, page_size)


# 🔍 2.4 Search with Date Range
@router.get("/date-range", tags=["Search: Advanced"])
@log_performance("Search: Date Range")
async def search_by_date_range_endpoint(
    q: str = Query(..., description="Medicine name"),
    user_id: str = Query(..., description="User ID"),
    start_date: str = Query(..., description="Start date in ISO format (YYYY-MM-DD)"),
    end_date: str = Query(..., description="End date in ISO format (YYYY-MM-DD)"),
    size: int = Query(10, ge=1, le=100, description="Max results to return")
) -> List[Dict[str, Any]]:
    """
    Search prescriptions by text and date range.
    Dates must be in ISO format: YYYY-MM-DD
    """
    result = await search_with_date_range(
        text=q,
        user_id=user_id,
        start_date=start_date,
        end_date=end_date,
        size=size
    )
    return _extract_hits(result)


# 🔍 2.5 Semantic Search Endpoint
@router.get("/semantic", tags=["Search: Advanced"])
@log_performance("Search: Semantic")
async def semantic_search_endpoint(
    q: str = Query(..., min_length=1, description="Search query"),
    user_id: str = Query(..., min_length=1, description="User ID"),
    size: int = Query(10, ge=1, le=100, description="Max results")
) -> Dict[str, Any]:
    """
    Production Vector Semantic Medicine Search using ANN.
    Matches prescriptions by meaning instead of exact keywords.
    """
    if not settings.ELASTICSEARCH_ENABLED:
        raise HTTPException(status_code=503, detail="Search service disabled")
        
    try:
        # Generate embedding for the query using the configured robust embedding service
        query_vector = embedding_service.embed_query(q)
        
        # Log the query for auditing
        logger.info(f"Executing semantic search for user: {user_id} with query: {q}")
        
        result = await es_service.semantic_search(
            query=q,
            user_id=user_id,
            query_vector=query_vector,
            size=size
        )
        
        hits = _extract_hits(result)
        
        # Apply Clinical Guardrails
        filtered_hits = []
        similarity_threshold = 0.65
        
        for hit in hits:
            # In ES 8 dense_vector cosine similarity mapping, the `_score` is usually (1 + cosine(a,b)) / 2 
            # Check the raw score from the hit
            # Handle None score (can happen when ES returns score as None)
            score = hit.get("_score") or 0.0
            
            # Filter below threshold
            if score < similarity_threshold:
                continue
                
            # Add confidence score and explainability metadata
            typed_score: float = float(score)
            hit["_semantic_metadata"] = {
                "confidence_score": round(typed_score, 4),
                "match_type": "semantic"
            }
            filtered_hits.append(hit)
            
        return {
            "results": filtered_hits,
            "metadata": {
                "total_returned": len(filtered_hits),
                "threshold_applied": similarity_threshold,
                "clinical_disclaimer": "Symptom matching is suggestive, not diagnostic. Do not use for definitive medical advice."
            }
        }
    except Exception as e:
        logger.error(f"Semantic search failed: {e}")
        raise HTTPException(status_code=500, detail="Semantic search failed")



# ⭐ 4.1 Hybrid Search Endpoint (A/B Testing)
@router.get("/hybrid", tags=["Search: Advanced"])
@log_performance("Search: Hybrid")
async def hybrid_search_endpoint(
    q: str = Query(..., min_length=1, description="Search query"),
    user_id: str = Query(..., min_length=1, description="User ID"),
    size: int = Query(10, ge=1, le=100, description="Max results")
) -> Dict[str, Any]:
    """
    Production Hybrid Search (BM25 + HNSW).
    Combines exact keyword matches with semantic meaning.
    Uses 0.7 BM25 + 0.3 Vector weighting setup.
    """
    if not settings.ELASTICSEARCH_ENABLED:
        raise HTTPException(status_code=503, detail="Search service disabled")
        
    try:
        query_vector = embedding_service.embed_query(q)
        
        logger.info(f"Executing hybrid search for user: {user_id} with query: {q}")
        
        result = await es_service.hybrid_search(
            query=q,
            user_id=user_id,
            query_vector=query_vector,
            size=size
        )
        
        hits = _extract_hits(result)
        
        # We can apply the same similarity guardrails if needed, 
        # or just return the hybrid results directly since BM25 anchors it.
        return {
            "results": hits,
            "metadata": {
                "total_returned": len(hits),
                "strategy": "hybrid (BM25 + Semantic HNSW)",
                "weights": "0.7 BM25 / 0.3 Vector"
            }
        }
    except Exception as e:
        logger.error(f"Hybrid search failed: {e}")
        raise HTTPException(status_code=500, detail="Hybrid search failed")


# ⭐ 5.1 Autocomplete Endpoint
@router.get("/autocomplete", tags=["Search: Discovery"])
@cached(ttl=300, key_prefix="search_autocomplete")
async def autocomplete(
    q: str = Query(..., description="Search text for autocomplete"),
    user_id: str = Query(..., description="User ID"),
    size: int = Query(10, ge=1, le=50, description="Max suggestions to return")
) -> List[Dict[str, Any]]:
    """
    Autocomplete search suggestions based on partial text input.
    Returns matching prescriptions across all fields.
    """
    result = await autocomplete_search(q, user_id, size)
    return _extract_hits(result)


# ⭐ 4.2 Fuzzy Search Endpoint
@router.get("/fuzzy", tags=["Search: Advanced"])
@cached(ttl=120, key_prefix="search_fuzzy")
@log_performance("Search: Fuzzy")
async def fuzzy(
    q: str = Query(..., description="Search text (handles typos)"),
    user_id: str = Query(..., description="User ID"),
    page: int = Query(1, ge=1, description="Page number (starts at 1)"),
    page_size: int = Query(10, ge=1, le=100, description="Results per page"),
    sort_by: str = Query("relevance", pattern="^(relevance|date)$", description="Sort by relevance or date")
) -> Dict[str, Any]:
    """
    Fuzzy search with typo tolerance across all fields.
    Returns paginated results with total count and metadata.
    """
    result = await fuzzy_search(q, user_id, page, page_size, sort_by)
    return _extract_paginated_response(result, page, page_size)


# ⭐ 6.1 Intent-Based Smart Search
@router.get("/comprehensive", tags=["Search: Intelligence"])
@log_performance("Search: Comprehensive Intent-Based")
async def intent_based_search(
    q: str = Query(..., description="Search text"),
    user_id: str = Query(..., description="User ID"),
    page: int = Query(1, ge=1, description="Page number (starts at 1)"),
    size: int = Query(10, ge=1, le=100, description="Results per page"),
    intent_classifier: IntentClassifier = Depends(get_intent_classifier),
    reranker: SemanticReranker = Depends(get_reranker)
) -> Dict[str, Any]:
    """
    Intelligent search endpoint that detects user intent and routes to the best search strategy.
    
    Routes:
    - **TEMPORAL_RECALL**: Date-filtered search (fallback to general list for now)
    - **SYMPTOM_SEARCH**: Semantic Vector search focused on embeddings
    - **MEDICINE_LOOKUP**: Lexical-boosted search for precise medicine matching
    - **DOCTOR_SEARCH**: Lexical-boosted search for doctor/hospital
    - **GENERAL**: Standard hybrid search
    """
    if not settings.ELASTICSEARCH_ENABLED:
        raise HTTPException(status_code=503, detail="Search service disabled")
        
    try:
        # Detect Intent
        intent_val = intent_classifier.detect_intent(q)
        intent_str = str(intent_val)
        logger.info(f"Query: '{q}', Detected Intent: {intent_str}")
        
        # We fetch more candidates for reranking stages
        fetch_size = size * 5 if intent_str in [SearchIntent.SYMPTOM_SEARCH.value, SearchIntent.GENERAL.value] else size
        
        # Initialize response with explicit type to handle mixed values
        response: Dict[str, Any] = {}
        
        # Route Strategy based on intent
        if intent_str == SearchIntent.TEMPORAL_RECALL.value:
            # Fallback for now; advanced would parse actual dates
            result = await search_all(q, user_id, page, size, "date")
            response = _extract_paginated_response(result, page, size)
            
        elif intent_str == SearchIntent.SYMPTOM_SEARCH.value:
            # Stage 1: Fast Vector Retrieval (ANN Top 50)
            query_vector = embedding_service.embed_query(q)
            res = await es_service.semantic_search(query=q, user_id=user_id, query_vector=query_vector, size=fetch_size)
            hits = _extract_hits(res)
            
            # Stage 2: Fine-grained Reranking (Cross-Encoder Top N)
            reranked_hits = reranker.rerank(query=q, candidates=hits, top_k=size, text_field="raw_text")
            
            response = {
                "total": len(hits) if "total" not in res else res["hits"].get("total", {}).get("value", len(hits)),
                "page": page, 
                "page_size": size, 
                "results": reranked_hits
            }
            
        elif intent_str == SearchIntent.DOCTOR_SEARCH.value:
            # Doctor / Hospital
            res = await search_by_doctor_or_hospital(q, user_id, size)
            hits = _extract_hits(res)
            response = {
                "total": len(hits), "page": page, "page_size": size, "results": hits
            }
            
        elif intent_str == SearchIntent.MEDICINE_LOOKUP.value:
            # Medicine
            res = await search_by_medicine(q, user_id, size)
            hits = _extract_hits(res)
            response = {
                "total": len(hits), "page": page, "page_size": size, "results": hits
            }
            
        else:
            # General Hybrid
            query_vector = embedding_service.embed_query(q)
            res = await es_service.hybrid_search(query=q, user_id=user_id, query_vector=query_vector, size=fetch_size)
            hits = _extract_hits(res)
            
            # Stage 2: Fine-grained Reranking
            reranked_hits = reranker.rerank(query=q, candidates=hits, top_k=size, text_field="raw_text")
            
            response = {
                "total": len(hits) if "total" not in res else res["hits"].get("total", {}).get("value", len(hits)),
                "page": page, 
                "page_size": size, 
                "results": reranked_hits
            }

        # Add intent metadata
        response["metadata"] = {
            "detected_intent": intent_str,
            "query": q,
            "reranked": intent_str in [SearchIntent.SYMPTOM_SEARCH.value, SearchIntent.GENERAL.value]
        }
        return response
        
    except Exception as e:
        logger.error(f"Intent search failed: {e}")
        raise HTTPException(status_code=500, detail="Search routing failed")


# ⭐ 7.1 Learning-to-Rank Logging Endpoint
class SearchInteraction(BaseModel):
    query: str
    prescription_id: str
    rank_position: int
    features: Optional[Dict[str, Any]] = None

@router.post("/interaction", summary="Log Search Interaction for LTR", tags=["Search: Management"])
@log_performance("Search: Log Interaction")
async def log_search_interaction(
    interaction: SearchInteraction,
    user_id: str = Query(..., description="User ID"),
    ltr: LTRService = Depends(get_ltr_service)
) -> Dict[str, Any]:
    """
    Log a search interaction (e.g., user clicked on a result).
    Used to build the Learning-to-Rank training dataset.
    """
    success = ltr.log_interaction(
        user_id=user_id,
        query=interaction.query,
        prescription_id=interaction.prescription_id,
        rank_position=interaction.rank_position,
        features=interaction.features
    )
    if not success:
        raise HTTPException(status_code=500, detail="Failed to log interaction")
    
    return {"status": "success", "message": "Interaction logged successfully"}

