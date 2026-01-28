# 🌐 Search API Endpoints
from typing import List, Any, Dict
from fastapi import APIRouter, Query, HTTPException
from app.services.search_indexer import (
    search_by_medicine,
    search_by_doctor_or_hospital,
    search_all,
    search_with_date_range,
    autocomplete_search,
    fuzzy_search
)

router = APIRouter()


def _extract_hits(result: Any) -> List[dict]:
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
@router.get("/medicine")
def search_medicine(
    q: str = Query(..., description="Medicine name"),
    user_id: str = Query(..., description="User ID"),
    size: int = Query(10, ge=1, le=100, description="Max results to return")
) -> List[dict]:
    """Search prescriptions by medicine name with fuzzy matching."""
    result = search_by_medicine(q, user_id, size)
    return _extract_hits(result)


# 🔍 2.2 Search by Doctor / Hospital
@router.get("/provider")
def search_provider(
    q: str = Query(..., description="Doctor name or hospital"),
    user_id: str = Query(..., description="User ID"),
    size: int = Query(10, ge=1, le=100, description="Max results to return")
) -> List[dict]:
    """Search prescriptions by doctor name or hospital."""
    result = search_by_doctor_or_hospital(q, user_id, size)
    return _extract_hits(result)


# 🔍 2.3 Universal Search (Recommended)
@router.get("/all")
def search_everything(
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
    result = search_all(q, user_id, page, page_size, sort_by)
    return _extract_paginated_response(result, page, page_size)


# 🔍 2.4 Search with Date Range
@router.get("/date-range")
def search_by_date_range_endpoint(
    q: str = Query(..., description="Medicine name"),
    user_id: str = Query(..., description="User ID"),
    start_date: str = Query(..., description="Start date in ISO format (YYYY-MM-DD)"),
    end_date: str = Query(..., description="End date in ISO format (YYYY-MM-DD)"),
    size: int = Query(10, ge=1, le=100, description="Max results to return")
) -> List[dict]:
    """
    Search prescriptions by text and date range.
    Dates must be in ISO format: YYYY-MM-DD
    """
    result = search_with_date_range(
        text=q,
        user_id=user_id,
        start_date=start_date,
        end_date=end_date,
        size=size
    )
    return _extract_hits(result)


# ⭐ 4.1 Autocomplete Endpoint
@router.get("/autocomplete")
def autocomplete(
    q: str = Query(..., description="Search text for autocomplete"),
    user_id: str = Query(..., description="User ID"),
    size: int = Query(10, ge=1, le=50, description="Max suggestions to return")
) -> List[dict]:
    """
    Autocomplete search suggestions based on partial text input.
    Returns matching prescriptions across all fields.
    """
    result = autocomplete_search(q, user_id, size)
    return _extract_hits(result)


# ⭐ 4.2 Fuzzy Search Endpoint
@router.get("/fuzzy")
def fuzzy(
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
    result = fuzzy_search(q, user_id, page, page_size, sort_by)
    return _extract_paginated_response(result, page, page_size)
