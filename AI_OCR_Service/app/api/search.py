import logging
from fastapi import APIRouter, HTTPException, Query

from app.services.search_indexer import search_prescriptions, get_indexed_prescription

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/prescriptions")
def search(
    q: str = Query(..., description="Search query — medicine name, doctor, hospital, etc."),
    size: int = Query(10, ge=1, le=100, description="Maximum number of results to return"),
):
    """
    Full-text search across all indexed prescriptions.

    Searches across: medicine names, doctor name, hospital, patient name.
    Supports fuzzy matching for minor spelling differences.
    """
    if not q.strip():
        raise HTTPException(status_code=400, detail="Search query cannot be empty.")

    logger.info("Search query: '%s' (size=%d)", q, size)
    results = search_prescriptions(query=q, size=size)

    return {
        "query": q,
        "total": len(results),
        "results": results,
    }


@router.get("/prescriptions/{prescription_id}")
def get_prescription(prescription_id: str):
    """
    Retrieve a single indexed prescription document by its ID.
    Returns 404 if not found or not yet indexed.
    """
    doc = get_indexed_prescription(prescription_id)
    if doc is None:
        raise HTTPException(
            status_code=404,
            detail=f"Prescription '{prescription_id}' not found in search index. "
                   "It may still be processing."
        )
    return doc
