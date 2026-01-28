import logging
from typing import Optional, Dict, Any, List, TYPE_CHECKING
from elasticsearch import Elasticsearch
from elastic_transport import ConnectionError as ESConnectionError
from app.core.config import settings
from datetime import datetime, timezone

from elasticsearch import Elasticsearch
from elasticsearch.exceptions import RequestError
import os

ES_HOST = os.getenv("ELASTICSEARCH_HOST", "http://localhost:9200")

ES_INDEX_ALIAS = "prescriptions_current"
NEW_INDEX = "prescriptions_v2"

MIGRATION_MODE = os.getenv("ES_MIGRATION_MODE", "false") == "true"

es = Elasticsearch(ES_HOST)

if TYPE_CHECKING:
    from elastic_transport import ObjectApiResponse

logger = logging.getLogger(__name__)

# Lazy initialization - don't connect at import time
_es_client: Optional[Elasticsearch] = None


def get_es_client() -> Optional[Elasticsearch]:
    """Get Elasticsearch client, creating it lazily if needed."""
    global _es_client
    
    if not settings.ELASTICSEARCH_ENABLED:
        return None
    
    if _es_client is None:
        _es_client = Elasticsearch(settings.ELASTICSEARCH_HOST)
    
    return _es_client


def _build_user_filter(user_id: str) -> Dict[str, Any]:
    """Build a user_id filter clause for ES queries."""
    return {"term": {"user_id": user_id}}


def index_prescription(prescription_id: str, data: dict, user_id: Optional[str] = None) -> bool:
    """
    Index prescription data to Elasticsearch.
    
    Args:
        prescription_id: Unique identifier for the prescription
        data: Dictionary containing prescription data (doctor_name, hospital, medicines)
        user_id: Optional user identifier for filtering in searches
    
    Returns:
        True if indexing was successful, False otherwise.
        Gracefully handles connection errors without crashing the application.
    """
    es = get_es_client()
    
    if es is None:
        logger.debug(
            f"Elasticsearch indexing skipped for prescription {prescription_id} "
            "(ELASTICSEARCH_ENABLED=false)"
        )
        return False
    
    # Extract medicine names safely, filtering out None values
    medicines = data.get("medicines", [])
    medicine_names: List[str] = [
        med.get("name") 
        for med in medicines 
        if med.get("name") is not None
    ]
    
    document: Dict[str, Any] = {
        "prescription_id": prescription_id,
        "user_id": data.get("user_id"),
        "doctor_name": data.get("doctor_name"),
        "hospital": data.get("hospital"),
        "medicine_names": [m.get("name") for m in data.get("medicines", [])],
        # "created_at": datetime.now(timezone.utc).isoformat(),
        "created_at": data.get("created_at")
    }
    
    # Always write to current alias
    es.index(index=ES_INDEX_ALIAS, id=prescription_id, document=document)

    # During migration, dual-write
    if MIGRATION_MODE:
        es.index(index=NEW_INDEX, id=prescription_id, document=document)
        
    # Include user_id if provided (required for user-scoped searches)
    if user_id is not None:
        document["user_id"] = user_id

    try:
        es.index(index=ES_INDEX_ALIAS, id=prescription_id, document=document)
        logger.info(f"Successfully indexed prescription {prescription_id} to Elasticsearch")
        return True
    except ESConnectionError as e:
        logger.warning(
            f"Elasticsearch connection failed for prescription {prescription_id}. "
            f"Indexing skipped. Error: {e}"
        )
        return False
    except Exception as e:
        logger.error(
            f"Unexpected error indexing prescription {prescription_id} to Elasticsearch: {e}"
        )
        return False


# 🔍 1.1 Search by Medicine Name
def search_by_medicine(
    medicine: str,
    user_id: str,
    size: int = 10
) -> Optional[ObjectApiResponse[Any]]:
    """
    Search prescriptions by medicine name with fuzzy matching.
    
    Args:
        medicine: Medicine name to search for
        user_id: User ID to filter results
        size: Maximum number of results to return
    
    Returns:
        Elasticsearch search results or None if ES is disabled/unavailable
    """
    es = get_es_client()
    
    if es is None:
        logger.debug("Elasticsearch search_by_medicine skipped (ELASTICSEARCH_ENABLED=false)")
        return None
    
    # try:
    #     return es.search(
    #         index=ES_INDEX,
    #         size=size,
    query={
                "bool": {
                    "must": [
                        {
                            "match": {
                                "medicine_names": {
                                    "query": medicine,
                                    "fuzziness": "AUTO"
                                }
                            }
                        }
                    ],
                    "filter": [_build_user_filter(user_id)]
                }
            }
    #     )
    # except ESConnectionError as e:
    #     logger.warning(f"Elasticsearch connection failed during medicine search: {e}")
    #     return None
    # except Exception as e:
    #     logger.error(f"Unexpected error during medicine search: {e}")
    #     return None
    return es.search(index=ES_INDEX_ALIAS, body=query)


# 🔍 1.2 Search by Doctor or Hospital
def search_by_doctor_or_hospital(
    query_text: str,
    user_id: str,
    size: int = 10
) -> Optional[ObjectApiResponse[Any]]:
    """
    Search prescriptions by doctor name or hospital.
    
    Args:
        query_text: Search text for doctor or hospital
        user_id: User ID to filter results
        size: Maximum number of results to return
    
    Returns:
        Elasticsearch search results or None if ES is disabled/unavailable
    """
    es = get_es_client()
    
    if es is None:
        logger.debug("Elasticsearch search_by_doctor_or_hospital skipped (ELASTICSEARCH_ENABLED=false)")
        return None
    
    # try:
    #     return es.search(
    #         index=ES_INDEX,
    #         size=size,
    query={
                "bool": {
                    "should": [
                        {"match": {"doctor_name": query_text}},
                        {"match": {"hospital": query_text}}
                    ],
                    "minimum_should_match": 1,
                    "filter": [_build_user_filter(user_id)]
                }
            }
        # )
    # except ESConnectionError as e:
    #     logger.warning(f"Elasticsearch connection failed during doctor/hospital search: {e}")
    #     return None
    # except Exception as e:
    #     logger.error(f"Unexpected error during doctor/hospital search: {e}")
    #     return None
    return es.search(index=ES_INDEX_ALIAS, body=query)


# 🔍 1.3 Combined Search (Medicine + Doctor + Hospital)
# 🧱 LAYER 2 + 3: Exact Match Priority + Recency Boost
def search_all(
    text: str,
    user_id: str,
    page: int = 1,
    page_size: int = 10,
    sort_by: str = "relevance"
) -> Optional[ObjectApiResponse[Any]]:
    """
    Advanced search with:
    - LAYER 2: Exact match > Partial match (match_phrase boost)
    - LAYER 3: Recency boost (gauss decay function)
    - Field boosting: Medicine > Doctor > Hospital
    
    Args:
        text: Search text
        user_id: User ID to filter results
        page: Page number for pagination
        page_size: Results per page
        sort_by: Sort by 'relevance' or 'date'
    
    Returns:
        Elasticsearch search results or None if ES is disabled/unavailable
    """
    es = get_es_client()
    
    if es is None:
        logger.debug("Elasticsearch search_all skipped (ELASTICSEARCH_ENABLED=false)")
        return None
    
    from_, size = build_pagination(page, page_size)

    sort_clause = (
        [{"created_at": {"order": "desc"}}]
        if sort_by == "date"
        else ["_score"]
    )

    # 🧱 LAYER 2 + 3: Function Score with Exact Match Priority + Recency
    query = {
        "from": from_,
        "size": size,
        "sort": sort_clause,
        "query": {
            "function_score": {
                "query": {
                    "bool": {
                        "should": [
                            # 🔥 LAYER 2: Exact phrase gets highest boost
                            {
                                "match_phrase": {
                                    "medicine_names": {
                                        "query": text,
                                        "boost": 8  # Exact wins
                                    }
                                }
                            },
                            # Standard match with high boost
                            {
                                "match": {
                                    "medicine_names": {
                                        "query": text,
                                        "boost": 5
                                    }
                                }
                            },
                            # Exact phrase for doctor
                            {
                                "match_phrase": {
                                    "doctor_name": {
                                        "query": text,
                                        "boost": 4
                                    }
                                }
                            },
                            # Standard doctor match
                            {
                                "match": {
                                    "doctor_name": {
                                        "query": text,
                                        "boost": 2
                                    }
                                }
                            },
                            # Exact phrase for hospital
                            {
                                "match_phrase": {
                                    "hospital": {
                                        "query": text,
                                        "boost": 2
                                    }
                                }
                            },
                            # Standard hospital match
                            {
                                "match": {
                                    "hospital": {
                                        "query": text,
                                        "boost": 1
                                    }
                                }
                            }
                        ],
                        "minimum_should_match": 1,
                        "filter": [
                            {"term": {"user_id": user_id}}
                        ]
                    }
                },
                # 🧱 LAYER 3: Recency Boost (Gauss Decay)
                "functions": [
                    {
                        "gauss": {
                            "created_at": {
                                "origin": "now",
                                "scale": "30d",  # Recent prescriptions within 30 days get boost
                                "decay": 0.5      # Older ones decay slowly
                            }
                        }
                    }
                ],
                "score_mode": "avg",     # Average function scores
                "boost_mode": "sum"      # Add to relevance score
            }
        }
    }
    
    return es.search(index=ES_INDEX_ALIAS, body=query)
    # except ESConnectionError as e:
    #     logger.warning(f"Elasticsearch connection failed during combined search: {e}")
    #     return None
    # except Exception as e:
    #     logger.error(f"Unexpected error during combined search: {e}")
    #     return None


# 🔍 1.4 Search with Date Range
def search_with_date_range(
    text: str,
    user_id: str,
    start_date: str,
    end_date: str,
    size: int = 10
) -> Optional[ObjectApiResponse[Any]]:
    """
    Search prescriptions by medicine name within a date range.
    
    Args:
        text: Medicine name to search for
        user_id: User ID to filter results
        start_date: Start date in ISO format (inclusive)
        end_date: End date in ISO format (inclusive)
        size: Maximum number of results to return
    
    Returns:
        Elasticsearch search results or None if ES is disabled/unavailable
    """
    es = get_es_client()
    
    if es is None:
        logger.debug("Elasticsearch search_with_date_range skipped (ELASTICSEARCH_ENABLED=false)")
        return None
    
    # try:
    #     return es.search(
    #         index=ES_INDEX,
    #         size=size,
    query={
                "bool": {
                    "must": [
                        {
                            "match": {
                                "medicine_names": {
                                    "query": text,
                                    "fuzziness": "AUTO"
                                }
                            }
                        }
                    ],
                    "filter": [
                        _build_user_filter(user_id),
                        {
                            "range": {
                                "created_at": {
                                    "gte": start_date,
                                    "lte": end_date
                                }
                            }
                        }
                    ]
                }
            }
    #     )
    # except ESConnectionError as e:
    #     logger.warning(f"Elasticsearch connection failed during date range search: {e}")
    #     return None
    # except Exception as e:
    #     logger.error(f"Unexpected error during date range search: {e}")
    #     return None
    return es.search(index=ES_INDEX_ALIAS, body=query)


def delete_prescription(prescription_id: str) -> bool:
    """
    Delete a prescription from Elasticsearch index.
    
    Args:
        prescription_id: ID of the prescription to delete
    
    Returns:
        True if deletion was successful, False otherwise
    """
    es = get_es_client()
    
    if es is None:
        logger.debug(
            f"Elasticsearch deletion skipped for prescription {prescription_id} "
            "(ELASTICSEARCH_ENABLED=false)"
        )
        return False
    
    try:
        es.delete(index=ES_INDEX_ALIAS, id=prescription_id)
        logger.info(f"Successfully deleted prescription {prescription_id} from Elasticsearch")
        return True
    except ESConnectionError as e:
        logger.warning(
            f"Elasticsearch connection failed for prescription {prescription_id} deletion. "
            f"Error: {e}"
        )
        return False
    except Exception as e:
        logger.error(
            f"Unexpected error deleting prescription {prescription_id} from Elasticsearch: {e}"
        )
        return False

# ⭐ 3.1 Autocomplete (Prefix Search)
# 🧱 LAYER 2: Exact Match Priority for Autocomplete
def autocomplete_search(text: str, user_id: str, size: int = 10):
    """
    Autocomplete search with exact match priority.
    Exact matches rank higher than partial/prefix matches.
    
    Args:
        text: Partial text for autocomplete
        user_id: User ID to filter results
        size: Maximum number of suggestions
    
    Returns:
        Elasticsearch search results or None if ES is disabled/unavailable
    """
    es = get_es_client()
    
    if es is None:
        logger.debug("Elasticsearch autocomplete_search skipped (ELASTICSEARCH_ENABLED=false)")
        return None
    
    query = {
        "size": size,
        "query": {
            "bool": {
                "should": [
                    # 🔥 Exact phrase gets highest priority
                    {
                        "match_phrase": {
                            "medicine_names": {
                                "query": text,
                                "boost": 10
                            }
                        }
                    },
                    # Standard match with high boost
                    {
                        "match": {
                            "medicine_names": {
                                "query": text,
                                "operator": "and",
                                "boost": 5
                            }
                        }
                    },
                    # Exact phrase for doctor
                    {
                        "match_phrase": {
                            "doctor_name": {
                                "query": text,
                                "boost": 5
                            }
                        }
                    },
                    # Standard doctor match
                    {
                        "match": {
                            "doctor_name": {
                                "query": text,
                                "boost": 2
                            }
                        }
                    },
                    # Exact phrase for hospital
                    {
                        "match_phrase": {
                            "hospital": {
                                "query": text,
                                "boost": 3
                            }
                        }
                    },
                    # Standard hospital match
                    {
                        "match": {
                            "hospital": {
                                "query": text,
                                "boost": 1
                            }
                        }
                    }
                ],
                "minimum_should_match": 1,
                "filter": [
                    {"term": {"user_id": user_id}}
                ]
            }
        }
    }

    return es.search(index=ES_INDEX_ALIAS, body=query)

# ⭐ 3.2 Fuzzy Search (Typos)
# 🧱 LAYER 4: Safe Fuzzy Tuning
def fuzzy_search(
    text: str,
    user_id: str,
    page: int = 1,
    page_size: int = 10,
    sort_by: str = "relevance"
) -> Optional[ObjectApiResponse[Any]]:
    """
    Fuzzy search with safe tuning to prevent wild matches.
    
    🧱 LAYER 4 Features:
    - prefix_length=2: Avoids wild matches by requiring exact first 2 chars
    - max_expansions=50: Performance safe, limits term expansion
    - Lower boost than exact match to maintain relevance hierarchy
    
    Args:
        text: Search text (handles typos)
        user_id: User ID to filter results
        page: Page number for pagination
        page_size: Results per page
        sort_by: Sort by 'relevance' or 'date'
    
    Returns:
        Elasticsearch search results or None if ES is disabled/unavailable
    """
    es = get_es_client()
    
    if es is None:
        logger.debug("Elasticsearch fuzzy_search skipped (ELASTICSEARCH_ENABLED=false)")
        return None
    
    from_, size = build_pagination(page, page_size)

    sort_clause = (
        [{"created_at": {"order": "desc"}}]
        if sort_by == "date"
        else ["_score"]
    )

    query = {
        "from": from_,
        "size": size,
        "sort": sort_clause,
        "query": {
            "bool": {
                "should": [
                    # 🧱 LAYER 4: Safe fuzzy for medicines (highest priority)
                    {
                        "match": {
                            "medicine_names": {
                                "query": text,
                                "fuzziness": "AUTO",
                                "prefix_length": 2,      # First 2 chars must match exactly
                                "max_expansions": 50,    # Limit expansions for performance
                                "boost": 3               # Lower than exact match
                            }
                        }
                    },
                    # Safe fuzzy for doctor
                    {
                        "match": {
                            "doctor_name": {
                                "query": text,
                                "fuzziness": "AUTO",
                                "prefix_length": 2,
                                "max_expansions": 50,
                                "boost": 1.5
                            }
                        }
                    },
                    # Safe fuzzy for hospital
                    {
                        "match": {
                            "hospital": {
                                "query": text,
                                "fuzziness": "AUTO",
                                "prefix_length": 2,
                                "max_expansions": 50,
                                "boost": 1
                            }
                        }
                    }
                ],
                "minimum_should_match": 1,
                "filter": [
                    {"term": {"user_id": user_id}}
                ]
            }
        }
    }

    return es.search(index=ES_INDEX_ALIAS, body=query)

# Pagination & Sorting Utilities (Service Layer)
def build_pagination(page: int, page_size: int):
    page = max(page, 1)
    page_size = min(max(page_size, 1), 50)  # cap size for safety
    return (page - 1) * page_size, page_size

# 🧱 STEP 2: Create Versioned Index with Mapping
def create_prescriptions_index(version: str):
    """
    Creates Elasticsearch index with search_as_you_type fields
    for autocomplete and fuzzy search.
    Safe to call multiple times.
    """

    # if es.indices.exists(index=ES_INDEX):
    #     return  # Index already exists
    es = get_es_client()
    if es is None:
        return

    if es.indices.exists(index=ES_INDEX_ALIAS):
        return
    
    index_name = f"prescriptions_{version}"

    if es.indices.exists(index=index_name):
        return index_name


    index_body = {
        "settings": {
            "analysis": {
                "analyzer": {
                    "lowercase_analyzer": {
                        "type": "custom",
                        "tokenizer": "standard",
                        "filter": ["lowercase"]
                    }
                }
            }
        },
        "mappings": {
            "properties": {
                "prescription_id": {"type": "keyword"},
                "user_id": {"type": "keyword"},
                "doctor_name": {"type": "search_as_you_type"},
                "hospital": {"type": "search_as_you_type"},
                "medicine_names": {"type": "search_as_you_type"},
                "created_at": {"type": "date"}
            }
        }
    }

    es.indices.create(index=index_name, body=index_body)
    return index_name

    # try:
    #     es.indices.create(index=ES_INDEX_ALIAS, body=index_body)
    #     print(f"✅ Elasticsearch index '{ES_INDEX_ALIAS}' created")
    # except RequestError as e:
    #     raise RuntimeError(f"Failed to create index: {e}")

# 🧱 STEP 3: Reindex Data (CRITICAL)
def reindex_prescriptions(old_index: str, new_index: str):
    body = {
        "source": {
            "index": old_index
        },
        "dest": {
            "index": new_index
        }
    }

    es.reindex(body=body, wait_for_completion=True)

# Atomically Switch Alias (Zero Downtime)
def switch_alias_to_new_index(new_index: str):
    actions = []

    # Remove alias from any existing index
    try:
        current = es.indices.get_alias(name="prescriptions_current")
        for idx in current.keys():
            actions.append({
                "remove": {
                    "index": idx,
                    "alias": "prescriptions_current"
                }
            })
    except:
        pass  # Alias does not exist yet

    # Add alias to new index
    actions.append({
        "add": {
            "index": new_index,
            "alias": "prescriptions_current"
        }
    })
    
    es.indices.update_aliases(body={"actions": actions})



def verify_reindex(old_index: str, new_index: str):
    old_count = es.count(index=old_index)["count"]
    new_count = es.count(index=new_index)["count"]

    if new_count < old_count:
        raise RuntimeError("❌ Reindex incomplete — aborting alias switch")
