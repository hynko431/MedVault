"""
Elasticsearch search indexer service for prescription data.

This module provides both synchronous and asynchronous interfaces for
indexing and searching prescription documents in Elasticsearch.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Protocol, Union

from tenacity import retry, stop_after_attempt, wait_exponential
if TYPE_CHECKING:
    from elasticsearch import NotFoundError, RequestError, AuthorizationException
    from elastic_transport import ConnectionError as ESConnectionError
else:
    try:
        from elasticsearch import NotFoundError, RequestError, AuthorizationException
        from elastic_transport import ConnectionError as ESConnectionError
    except ImportError:
        # Fallback for type checking or missing dependencies
        class NotFoundError(Exception): pass # type: ignore
        class RequestError(Exception): pass # type: ignore
        class AuthorizationException(Exception): pass # type: ignore
        class ESConnectionError(Exception): pass # type: ignore

from app.core.config.config import settings
from app.core.logging.logger import get_logger
from app.core.logging.async_logger import log_performance

logger = get_logger(__name__)

# Type checking imports
if TYPE_CHECKING:
    from elastic_transport import ObjectApiResponse


# ============================================================================
# Configuration & Constants
# ============================================================================

DEFAULT_PAGE_SIZE = 10
MAX_PAGE_SIZE = 100
MAX_RETRIES = 3
RETRY_WAIT_MIN = 2
RETRY_WAIT_MAX = 10

# Field boost values for relevance scoring
BOOST_EXACT_MATCH = 8.0
BOOST_MEDICINE_HIGH = 5.0
BOOST_DOCTOR_EXACT = 4.0
BOOST_MEDICINE_STANDARD = 3.0
BOOST_DOCTOR_STANDARD = 2.0
BOOST_HOSPITAL_EXACT = 2.0
BOOST_HOSPITAL_STANDARD = 1.0
BOOST_FUZZY_MEDICINE = 2.5  # Tuned for balance
BOOST_FUZZY_DOCTOR = 1.5
BOOST_FUZZY_HOSPITAL = 1.0

# Fuzzy search configuration
FUZZY_PREFIX_LENGTH = 1  # Better recall for short names
FUZZY_MAX_EXPANSIONS = 100  # More comprehensive matching
FUZZY_FUZZINESS = "AUTO"

# Recency scoring configuration
RECENCY_SCALE = "30d"
RECENCY_DECAY = 0.5
RECENCY_ORIGIN = "now"


# ============================================================================
# Search Strategy Enum (Feature Flag Pattern)
# ============================================================================

class SearchStrategy(str, Enum):
    """Search strategy options for autocomplete queries."""
    PREFIX_ONLY = "prefix"        # Fast prefix-only matching
    PREFIX_FUZZY = "prefix_fuzzy"  # Prefix + fuzzy combined (default)


# ============================================================================
# Data Models
# ============================================================================

@dataclass(frozen=True)
class PaginationParams:
    """Pagination parameters with validation."""
    page: int = 1
    page_size: int = DEFAULT_PAGE_SIZE
    
    def __post_init__(self) -> None:
        object.__setattr__(self, 'page', max(self.page, 1))
        object.__setattr__(self, 'page_size', min(max(self.page_size, 1), MAX_PAGE_SIZE))
    
    @property
    def from_offset(self) -> int:
        """Calculate the from offset for ES queries."""
        return (self.page - 1) * self.page_size


@dataclass(frozen=True)
class SearchResult:
    """Standardized search result container."""
    hits: List[Dict[str, Any]]
    total: int
    page: int
    page_size: int
    took_ms: int


# ============================================================================
# Exceptions
# ============================================================================

class ElasticsearchServiceError(Exception):
    """Base exception for Elasticsearch service errors."""
    pass


class ElasticsearchConnectionError(ElasticsearchServiceError):
    """Raised when Elasticsearch connection fails."""
    pass


class IndexError(ElasticsearchServiceError):
    """Raised when index operations fail."""
    pass


# ============================================================================
# Protocol for type hinting
# ============================================================================

class IndicesClient(Protocol):
    """Protocol for Elasticsearch indices client."""
    
    def exists(self, *, index: str) -> bool:
        """Check if an index exists."""
        ...
    
    def create(self, *, index: str, body: Dict[str, Any]) -> Any:
        """Create a new index."""
        ...
    
    def delete(self, *, index: str, ignore_unavailable: bool = True) -> Any:
        """Delete an index."""
        ...

    def get_alias(self, *, name: str) -> Dict[str, Any]:
        """Get alias information."""
        ...
    
    def update_aliases(self, *, body: Dict[str, Any]) -> Any:
        """Update aliases atomically."""
        ...


class ElasticsearchClient(Protocol):
    """Protocol for Elasticsearch client interface."""
    
    def index(self, *, index: str, id: str, document: Dict[str, Any]) -> Any:
        ...
    
    def search(self, *, index: str, body: Dict[str, Any]) -> Any:
        ...
    
    def delete(self, *, index: str, id: str) -> Any:
        ...
    
    def count(self, *, index: str) -> Dict[str, Any]:
        ...
    
    def reindex(self, *, body: Dict[str, Any], wait_for_completion: bool = True) -> Any:
        ...
    
    @property
    def indices(self) -> IndicesClient:
        """Return the indices client."""
        ...


# ============================================================================
# Client Factory (Deprecated - Use es_client_manager directly)
# ============================================================================

class ElasticsearchClientFactory:
    """
    Factory for creating Elasticsearch clients - DEPRECATED.
    
    This class is maintained for backward compatibility.
    Use es_client_manager from app.core.es_client for new code.
    """
    
    # Cache slot used by AsyncSearchService.close() to reset the client
    _async_client: "ClassVar[Optional[Any]]" = None  # type: ignore[misc]

    @classmethod
    def get_sync_client(cls) -> Optional[ElasticsearchClient]:
        """
        Get or create synchronous Elasticsearch client.
        
        Deprecated: Use es_client_manager.get_sync_client() instead.
        
        Returns:
            Elasticsearch client instance or None if ES is disabled.
        """
        from app.core.db.es_client import es_client_manager
        return es_client_manager.get_sync_client()
    
    @classmethod
    def get_async_client(cls) -> Optional[Any]:
        """
        Get or create asynchronous Elasticsearch client.
        
        Deprecated: Use es_client_manager.get_async_client() instead.
        
        Returns:
            AsyncElasticsearch client instance or None if ES is disabled.
        """
        from app.core.db.es_client import es_client_manager
        return es_client_manager.get_async_client()
    
    @classmethod
    def close_clients(cls) -> None:
        """
        Close all cached client connections.
        
        Deprecated: Use es_client_manager.close() instead.
        """
        # Async client closing is handled by es_client_manager
        pass


# ============================================================================
# Query Builders
# ============================================================================

class QueryBuilder:
    """Builder for constructing Elasticsearch queries."""
    
    @staticmethod
    def build_user_filter(user_id: str) -> Dict[str, Any]:
        """Build a user_id filter clause for ES queries."""
        return {"term": {"user_id": user_id}}
    
    @classmethod
    def build_hardened_production_query(cls, query_text: str, user_id: str, size: int = 10) -> Dict[str, Any]:
        """
        Build a multi-layered, production-grade ranking query.
        
        Optimized for:
        - Layer 1: Exact Medicine Phrase (Boost 10)
        - Layer 2: Fuzzy Medicine Match (Boost 6)
        - Layer 3: Diagnosis Match (Boost 4)
        - Layer 4: Raw OCR Fallback (Boost 2)
        - Recency: Exponential Decay (30d)
        - Performance: Strict Source Filtering & Atomic Isolation
        """
        base_query = {
            "bool": {
                "filter": [cls.build_user_filter(user_id)],
                "should": [
                    # Layer 1: Exact Medicine Phrase Match (Nested)
                    {
                        "nested": {
                            "path": "medicines",
                            "score_mode": "max",
                            "query": {
                                "match_phrase": {
                                    "medicines.name": {
                                        "query": query_text,
                                        "boost": 10.0
                                    }
                                }
                            }
                        }
                    },
                    # Layer 2: Fuzzy Medicine Match (Nested)
                    {
                        "nested": {
                            "path": "medicines",
                            "score_mode": "max",
                            "query": {
                                "match": {
                                    "medicines.name": {
                                        "query": query_text,
                                        "fuzziness": "AUTO",
                                        "boost": 6.0
                                    }
                                }
                            }
                        }
                    },
                    # Layer 3: Diagnosis Match
                    {
                        "match": {
                            "diagnosis": {
                                "query": query_text,
                                "boost": 4.0
                            }
                        }
                    },
                    # Layer 4: Raw OCR Fallback (Fuzzy)
                    {
                        "match": {
                            "raw_text": {
                                "query": query_text,
                                "fuzziness": "AUTO",
                                "boost": 2.0
                            }
                        }
                    }
                ],
                "minimum_should_match": 1
            }
        }

        return {
            "size": size,
            "track_total_hits": False,
            "_source": [
                "prescription_id",
                "doctor_name",
                "diagnosis",
                "created_at"
            ],
            "query": {
                "function_score": {
                    "query": base_query,
                    "functions": [
                        {
                            "exp": {
                                "created_at": {
                                    "origin": RECENCY_ORIGIN,
                                    "scale": RECENCY_SCALE,
                                    "decay": RECENCY_DECAY
                                }
                            }
                        }
                    ],
                    "score_mode": "sum",
                    "boost_mode": "sum"
                }
            }
        }

    @classmethod
    def build_medicine_search(cls, medicine: str, user_id: str, size: int) -> Dict[str, Any]:
        """Build query for medicine name search using the hardened pattern."""
        return cls.build_hardened_production_query(medicine, user_id, size)

    @classmethod
    def build_doctor_hospital_search(cls, query_text: str, user_id: str, size: int) -> Dict[str, Any]:
        """Build query for doctor/hospital search using the hardened pattern."""
        return cls.build_hardened_production_query(query_text, user_id, size)
    
    @classmethod
    def build_combined_search(
        cls,
        text: str,
        user_id: str,
        pagination: PaginationParams,
        sort_by: str = "relevance"
    ) -> Dict[str, Any]:
        """
        Build advanced search query with exact match priority and recency boost.
        
        Layer 2: Exact match > Partial match (match_phrase boost)
        Layer 3: Recency boost (gauss decay function)
        Field boosting: Medicine > Doctor > Hospital
        """
        sort_clause = (
            [{"created_at": {"order": "desc"}}]
            if sort_by == "date"
            else ["_score"]
        )

        return {
            "from": pagination.from_offset,
            "size": pagination.page_size,
            "sort": sort_clause,
            "query": {
                "function_score": {
                    "query": {
                        "bool": {
                            "should": [
                                # Layer 2: Exact phrase gets highest boost
                                {
                                    "match_phrase": {
                                        "medicine_names": {
                                            "query": text,
                                            "boost": BOOST_EXACT_MATCH
                                        }
                                    }
                                },
                                # Exact phrase synonym match
                                {
                                    "match_phrase": {
                                        "medicine_names.synonym": {
                                            "query": text,
                                            "boost": BOOST_EXACT_MATCH * 0.9
                                        }
                                    }
                                },
                                # Standard match with high boost
                                {
                                    "match": {
                                        "medicine_names": {
                                            "query": text,
                                            "boost": BOOST_MEDICINE_HIGH
                                        }
                                    }
                                },
                                # Synonym standard match
                                {
                                    "match": {
                                        "medicine_names.synonym": {
                                            "query": text,
                                            "boost": BOOST_MEDICINE_HIGH * 0.9
                                        }
                                    }
                                },
                                # Exact phrase for doctor
                                {
                                    "match_phrase": {
                                        "doctor_name": {
                                            "query": text,
                                            "boost": BOOST_DOCTOR_EXACT
                                        }
                                    }
                                },
                                # Standard doctor match
                                {
                                    "match": {
                                        "doctor_name": {
                                            "query": text,
                                            "boost": BOOST_DOCTOR_STANDARD
                                        }
                                    }
                                },
                                # Exact phrase for hospital
                                {
                                    "match_phrase": {
                                        "hospital": {
                                            "query": text,
                                            "boost": BOOST_HOSPITAL_EXACT
                                        }
                                    }
                                },
                                # Standard hospital match
                                {
                                    "match": {
                                        "hospital": {
                                            "query": text,
                                            "boost": BOOST_HOSPITAL_STANDARD
                                        }
                                    }
                                }
                            ],
                            "minimum_should_match": 1,
                            "filter": [cls.build_user_filter(user_id)]
                        }
                    },
                    # Layer 3: Recency Boost (Gauss Decay)
                    "functions": [
                        {
                            "gauss": {
                                "created_at": {
                                    "origin": "now",
                                    "scale": RECENCY_SCALE,
                                    "decay": RECENCY_DECAY
                                }
                            }
                        }
                    ],
                    "score_mode": "avg",
                    "boost_mode": "sum"
                }
            }
        }
    
    @classmethod
    def build_date_range_search(
        cls,
        text: str,
        user_id: str,
        start_date: str,
        end_date: str,
        size: int
    ) -> Dict[str, Any]:
        """Build query for date range search."""
        return {
            "size": size,
            "query": {
                "bool": {
                    "must": [
                        {
                            "multi_match": {
                                "query": text,
                                "fields": ["medicine_names", "medicine_names.synonym"],
                                "fuzziness": "AUTO"
                            }
                        }
                    ],
                    "filter": [
                        cls.build_user_filter(user_id),
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
        }
    
    @classmethod
    def build_autocomplete_search(cls, text: str, user_id: str, size: int) -> Dict[str, Any]:
        """
        Build production-grade autocomplete query using bool_prefix.
        
        Leverages search_as_you_type fields which internally create
        shingles and edge-ngrams for high-performance suggestions.
        
        V8 Enhancements:
        - Nested medicine support (Boost 5)
        - Source filtering disabled (_source: false)
        - Dedicated fields return
        - High-speed scoring
        """
        return {
            "size": size,
            "_source": False,
            "fields": [
                "doctor_name",
                "hospital",
                "medicines.name"
            ],
            "query": {
                "bool": {
                    "filter": [cls.build_user_filter(user_id)],
                    "should": [
                        # Root Level Autocomplete (Doctors / Hospitals)
                        {
                            "multi_match": {
                                "query": text,
                                "type": "bool_prefix",
                                "fields": [
                                    "doctor_name",
                                    "doctor_name._2gram",
                                    "doctor_name._3gram",
                                    "hospital",
                                    "hospital._2gram",
                                    "hospital._3gram"
                                ],
                                "boost": 2.0
                            }
                        },
                        # Nested Level Autocomplete (Medicines)
                        {
                            "nested": {
                                "path": "medicines",
                                "query": {
                                    "multi_match": {
                                        "query": text,
                                        "type": "bool_prefix",
                                        "fields": [
                                            "medicines.name",
                                            "medicines.name._2gram",
                                            "medicines.name._3gram"
                                        ],
                                        "boost": 5.0
                                    }
                                }
                            }
                        }
                    ],
                    "minimum_should_match": 1
                }
            }
        }
    
    @classmethod
    def build_fuzzy_search(
        cls,
        text: str,
        user_id: str,
        pagination: PaginationParams,
        sort_by: str = "relevance"
    ) -> Dict[str, Any]:
        """
        Build fuzzy search query with optimized production tuning.
        """
        sort_clause = (
            [{"created_at": {"order": "desc"}}]
            if sort_by == "date"
            else ["_score"]
        )

        return {
            "from": pagination.from_offset,
            "size": pagination.page_size,
            "sort": sort_clause,
            "query": {
                "bool": {
                    "should": [
                        # Layer 4: Safe fuzzy for medicines (highest priority)
                        {
                            "match": {
                                "medicine_names": {
                                    "query": text,
                                    "fuzziness": FUZZY_FUZZINESS,
                                    "prefix_length": FUZZY_PREFIX_LENGTH,
                                    "max_expansions": FUZZY_MAX_EXPANSIONS,
                                    "boost": BOOST_FUZZY_MEDICINE
                                }
                            }
                        },
                        # Safe fuzzy for doctor
                        {
                            "match": {
                                "doctor_name": {
                                    "query": text,
                                    "fuzziness": FUZZY_FUZZINESS,
                                    "prefix_length": FUZZY_PREFIX_LENGTH,
                                    "max_expansions": FUZZY_MAX_EXPANSIONS,
                                    "boost": BOOST_FUZZY_DOCTOR
                                }
                            }
                        },
                        # Safe fuzzy for hospital
                        {
                            "match": {
                                "hospital": {
                                    "query": text,
                                    "fuzziness": FUZZY_FUZZINESS,
                                    "prefix_length": FUZZY_PREFIX_LENGTH,
                                    "max_expansions": FUZZY_MAX_EXPANSIONS,
                                    "boost": BOOST_FUZZY_HOSPITAL
                                }
                            }
                        }
                    ],
                    "minimum_should_match": 1,
                    "filter": [cls.build_user_filter(user_id)]
                }
            }
        }
    
    @classmethod
    def build_semantic_search(
        cls,
        user_id: str,
        query_vector: List[float],
        size: int = 10
    ) -> Dict[str, Any]:
        """
        Build Production vector Semantic Search Query (HNSW).
        
        Uses native Elasticsearch 8+ Approximate kNN to retrieve semantically
        similar prescriptions based on the symptom query embedding vector.
        
        Args:
            user_id: User ID for filtering (security)
            query_vector: Embedding vector for semantic search
            size: Maximum number of results
            
        Returns:
            Elasticsearch query body as Python dict
        """
        return {
            "size": size,
            "knn": {
                "field": "embedding_vector",
                "query_vector": query_vector,
                "k": size,
                "num_candidates": 100,
                "filter": [
                    {"term": {"user_id": user_id}}
                ]
            }
        }

    @classmethod
    def build_advanced_hybrid_query(
        cls,
        query: str,
        user_id: str,
        query_vector: List[float],
        size: int = 10
    ) -> Dict[str, Any]:
        """
        Build Advanced Hybrid Search Query (BM25 + Script Score Vector).
        
        Production pattern:
        - BM25 as base filter/fetch (70% weight)
        - script_score with cosineSimilarity for reranking (30% weight)
        - Strict user_id filtering
        - Performance hardened (track_total_hits: False)
        """
        return {
            "size": size,
            "track_total_hits": False,
            "query": {
                "script_score": {
                    "query": {
                        "bool": {
                            "filter": [cls.build_user_filter(user_id)],
                            "should": [
                                # Global Lexical match
                                {
                                    "multi_match": {
                                        "query": query,
                                        "type": "bool_prefix",
                                        "fields": [
                                            "doctor_name^2",
                                            "hospital",
                                            "medicine_names^3",
                                            "medicine_names._2gram",
                                            "medicine_names._3gram"
                                        ]
                                    }
                                },
                                # Nested Medicine match
                                {
                                    "nested": {
                                        "path": "medicines",
                                        "score_mode": "avg",
                                        "query": {
                                            "match": {
                                                "medicines.name": {
                                                    "query": query,
                                                    "fuzziness": "AUTO",
                                                    "prefix_length": 2
                                                }
                                            }
                                        }
                                    }
                                }
                            ],
                            "minimum_should_match": 1
                        }
                    },
                    "script": {
                        "source": """
                            double vectorScore = (cosineSimilarity(params.query_vector, 'embedding_vector') + 1.0) / 2.0;
                            return (_score * 0.7) + (vectorScore * 0.3);
                        """,
                        "params": {
                            "query_vector": query_vector
                        }
                    }
                }
            }
        }

    @classmethod
    def build_hybrid_search(
        cls,
        query: str,
        user_id: str,
        query_vector: List[float],
        size: int = 5
    ) -> Dict[str, Any]:
        """Backward compatibility: delegates to advanced hybrid query."""
        return cls.build_advanced_hybrid_query(query, user_id, query_vector, size)

    @classmethod
    def build_nested_medicine_query(
        cls,
        medicine: str,
        user_id: str,
        size: int = DEFAULT_PAGE_SIZE
    ) -> Dict[str, Any]:
        """
        Build nested medicine query for searching within prescriptions.
        
        Uses nested queries to search through structured_data.medicines.name
        with phrase matching and fuzzy matching for better results.
        
        Args:
            medicine: Medicine name to search for
            user_id: User ID to filter results
            size: Maximum number of results to return
            
        Returns:
            Elasticsearch query body as dict
        """
        return {
            "size": size,
            "query": {
                "bool": {
                    "filter": [cls.build_user_filter(user_id)],
                    "should": [
                        # Exact phrase match for medicine name (nested)
                        {
                            "nested": {
                                "path": "medicines",
                                "query": {
                                    "match_phrase": {
                                        "medicines.name": {
                                            "query": medicine,
                                            "boost": 10.0
                                        }
                                    }
                                }
                            }
                        },
                        # Fuzzy match for medicine name (nested)
                        {
                            "nested": {
                                "path": "medicines",
                                "query": {
                                    "match": {
                                        "medicines.name": {
                                            "query": medicine,
                                            "fuzziness": FUZZY_FUZZINESS,
                                            "prefix_length": FUZZY_PREFIX_LENGTH,
                                            "boost": 5.0
                                        }
                                    }
                                }
                            }
                        },
                        # Fallback to flat medicine_names field
                        {
                            "match": {
                                "medicine_names": {
                                    "query": medicine,
                                    "fuzziness": FUZZY_FUZZINESS,
                                    "prefix_length": FUZZY_PREFIX_LENGTH,
                                    "boost": BOOST_FUZZY_MEDICINE
                                }
                            }
                        }
                    ],
                    "minimum_should_match": 1
                }
            }
        }


# ============================================================================
# Document Builder
# ============================================================================

class DocumentBuilder:
    """Builder for constructing prescription documents for Elasticsearch indexing."""
    
    @staticmethod
    def build_prescription_document(
        prescription_id: str,
        data: Dict[str, Any],
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Build a prescription document for indexing from DynamicPrescriptionExtracted schema.
        
        Args:
            prescription_id: Unique identifier for the prescription
            data: Dictionary containing prescription data (DynamicPrescriptionExtracted format)
            user_id: Optional user identifier for filtering
            Document dictionary ready for indexing
        """
        # Extract medicine names from the nested medicines array
        medicines = data.get("medicines", [])
        medicine_names = []
        for med in medicines:
            if isinstance(med, dict):
                name = med.get("name")
                if name:
                    medicine_names.append(name)
        
        # Extract doctor name from nested doctor object or legacy doctor_name field
        doctor_name = None
        doctor_data = data.get("doctor")
        if isinstance(doctor_data, dict):
            # Try nested doctor object first
            doctor_name = doctor_data.get("name")
            if not doctor_name:
                names = doctor_data.get("names")
                if isinstance(names, list) and names:
                    doctor_name = names[0]
        if not doctor_name:
            # Fall back to legacy doctor_name field
            doctor_name = data.get("doctor_name")
            if isinstance(doctor_name, list) and doctor_name:
                doctor_name = doctor_name[0]
        
        # Extract hospital name from nested hospital object or legacy field
        hospital = None
        hospital_data = data.get("hospital")
        if isinstance(hospital_data, dict):
            hospital = hospital_data.get("name")
        if not hospital:
            hospital = data.get("hospital_name") or data.get("hospital")
        
        # Extract patient name
        patient_name = None
        patient_data = data.get("patient")
        if isinstance(patient_data, dict):
            patient_name = patient_data.get("name")
        if not patient_name:
            patient_name = data.get("patient_name")
        
        # Extract diagnosis
        diagnosis = data.get("diagnosis", [])
        if isinstance(diagnosis, str):
            diagnosis = [diagnosis]
        
        # Build the document with flattened searchable fields
        document: Dict[str, Any] = {
            "prescription_id": prescription_id,
            "user_id": user_id or data.get("user_id"),
            "doctor_name": doctor_name,
            "hospital": hospital,
            "patient_name": patient_name,
            "medicine_names": medicine_names,
            "diagnosis": diagnosis,
            "medicines": medicines,  # Keep full nested structure
            "doctor": doctor_data,   # Keep full nested structure
            "hospital_info": hospital_data,  # Keep full nested structure
            "patient": patient_data,  # Keep full nested structure
            "raw_text": DocumentBuilder._build_raw_text(data),
            "created_at": data.get("created_at") or datetime.now(timezone.utc).isoformat()
        }
        
        # Add any additional metadata
        if "extraction_metadata" in data:
            document["extraction_metadata"] = data["extraction_metadata"]
        
        return document
    
    @staticmethod
    def _build_raw_text(data: Dict[str, Any]) -> str:
        """Build searchable raw text from all prescription fields."""
        text_parts = []
        
        # Add medicine names
        medicines = data.get("medicines", [])
        for med in medicines:
            if isinstance(med, dict):
                for key, value in med.items():
                    if value and key != "additional_info":
                        text_parts.append(str(value))
        
        # Add doctor info
        doctor = data.get("doctor", {})
        if isinstance(doctor, dict):
            if doctor.get("name"):
                text_parts.append(doctor["name"])
            if doctor.get("specialization"):
                text_parts.append(doctor["specialization"])
        
        # Add hospital info
        hospital = data.get("hospital", {})
        if isinstance(hospital, dict):
            if hospital.get("name"):
                text_parts.append(hospital["name"])
        
        # Add patient info
        patient = data.get("patient", {})
        if isinstance(patient, dict):
            if patient.get("name"):
                text_parts.append(patient["name"])
        
        # Add diagnosis
        diagnosis = data.get("diagnosis", [])
        if isinstance(diagnosis, list):
            text_parts.extend(diagnosis)
        elif isinstance(diagnosis, str):
            text_parts.append(diagnosis)
        
        # Add symptoms
        symptoms = data.get("symptoms", [])
        if isinstance(symptoms, list):
            text_parts.extend(symptoms)
        
        # Add advice
        advice = data.get("advice", [])
        if isinstance(advice, list):
            text_parts.extend(advice)
        
        return " ".join(text_parts)


# ============================================================================
# Synchronous Service
# ============================================================================

class SyncSearchService:
    """
    Synchronous Elasticsearch service for prescription search operations.
    
    This service provides blocking operations for indexing and searching
    prescription documents.
    """
    
    def __init__(self, client: Optional[ElasticsearchClient] = None):
        """
        Initialize the sync search service.
        
        Args:
            client: Optional Elasticsearch client. If not provided,
                   will get from factory.
        """
        self._client = client or ElasticsearchClientFactory.get_sync_client()
        self._index_alias = getattr(settings, 'ES_INDEX_ALIAS', "prescriptions_current")
        self._write_index = getattr(settings, 'ES_WRITE_INDEX', "prescriptions-prod-write")
        self._migration_mode = getattr(settings, 'ES_MIGRATION_MODE', False)
        self._new_index = getattr(settings, 'ES_NEW_INDEX', "prescriptions_v2")
    
    def _is_enabled(self) -> bool:
        """Check if Elasticsearch is enabled and available."""
        return self._client is not None

    def _extract_search_result(self, result: Dict[str, Any], pagination: Optional[PaginationParams] = None) -> SearchResult:
        """
        Extract standardized search results from raw Elasticsearch response.
        """
        hits = result.get("hits", {})
        total_info = hits.get("total", {})
        total_count = total_info.get("value", 0) if isinstance(total_info, dict) else total_info
        
        return SearchResult(
            hits=hits.get("hits", []),
            total=int(total_count),
            page=pagination.page if pagination else 1,
            page_size=pagination.page_size if pagination else len(hits.get("hits", [])),
            took_ms=int(result.get("took", 0))
        )
    
    def _execute_search(self, query: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Execute search with comprehensive error handling.
        
        Args:
            query: Elasticsearch query body
        
        Returns:
            Search results or None on error
        """
        if not self._is_enabled():
            logger.debug("Elasticsearch search skipped (disabled)")
            return None
        
        # Explicit None check for type safety
        if self._client is None:
            return None
            
        try:
            return self._client.search(index=self._index_alias, body=query)
        except ESConnectionError as e:
            logger.warning(f"Elasticsearch connection failed during search: {e}")
            return None
        except NotFoundError as e:
            logger.error(f"Elasticsearch index not found: {self._index_alias}. Error: {e}")
            return None
        except RequestError as e:
            logger.error(f"Elasticsearch query error: {e}")
            return None
        except AuthorizationException as e:
            logger.error(f"Elasticsearch authentication error: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error during search: {type(e).__name__}: {e}")
            return None
    
    def index_prescription(
        self,
        prescription_id: str,
        data: Dict[str, Any],
        user_id: Optional[str] = None
    ) -> bool:
        """
        Index prescription data to Elasticsearch.
        
        Args:
            prescription_id: Unique identifier for the prescription
            data: Dictionary containing prescription data
            user_id: Optional user identifier for filtering
        
        Returns:
            True if indexing was successful, False otherwise
        """
        if not self._is_enabled():
            logger.debug(
                f"Elasticsearch indexing skipped for prescription {prescription_id} "
                "(disabled)"
            )
            return False
        
        # Explicit None check for type safety
        if self._client is None:
            return False
        
        document = DocumentBuilder.build_prescription_document(
            prescription_id, data, user_id
        )
        
        try:
            from elastic_transport import ConnectionError as ESConnectionError
            
            # Always write to current write alias
            self._client.index(
                index=self._write_index,
                id=prescription_id,
                document=document
            )
            
            # During migration, dual-write
            if self._migration_mode:
                self._client.index(
                    index=self._new_index,
                    id=prescription_id,
                    document=document
                )
            
            logger.info(
                f"Successfully indexed prescription {prescription_id} to Elasticsearch"
            )
            return True
            
        except ESConnectionError as e:
            logger.warning(
                f"Elasticsearch connection failed for prescription {prescription_id}. "
                f"Indexing skipped. Error: {e}"
            )
            return False
        except Exception as e:
            logger.error(
                f"Unexpected error indexing prescription {prescription_id} "
                f"to Elasticsearch: {e}"
            )
            return False
    
    def search_by_medicine(
        self,
        medicine: str,
        user_id: str,
        size: int = DEFAULT_PAGE_SIZE
    ) -> Optional[SearchResult]:
        """
        Search prescriptions by medicine name with fuzzy matching.
        
        Args:
            medicine: Medicine name to search for
            user_id: User ID to filter results
            size: Maximum number of results to return
        
        Returns:
            Elasticsearch search results or None if disabled/unavailable
        """
        query = QueryBuilder.build_medicine_search(medicine, user_id, size)
        res = self._execute_search(query)
        if res is None:
            return None
        return self._extract_search_result(res)
    
    def search_by_doctor_or_hospital(
        self,
        query_text: str,
        user_id: str,
        size: int = DEFAULT_PAGE_SIZE
    ) -> Optional[SearchResult]:
        """
        Search prescriptions by doctor name or hospital.
        
        Args:
            query_text: Search text for doctor or hospital
            user_id: User ID to filter results
            size: Maximum number of results to return
        
        Returns:
            Elasticsearch search results or None if disabled/unavailable
        """
        query = QueryBuilder.build_doctor_hospital_search(query_text, user_id, size)
        res = self._execute_search(query)
        if res is None:
            return None
        return self._extract_search_result(res)
    
    def search_all(
        self,
        text: str,
        user_id: str,
        page: int = 1,
        page_size: int = DEFAULT_PAGE_SIZE,
        sort_by: str = "relevance"
    ) -> Optional[SearchResult]:
        """
        Advanced search with exact match priority and recency boost.
        
        Args:
            text: Search text
            user_id: User ID to filter results
            page: Page number for pagination
            page_size: Results per page
            sort_by: Sort by 'relevance' or 'date'
        
        Returns:
            Elasticsearch search results or None if disabled/unavailable
        """
        pagination = PaginationParams(page=page, page_size=page_size)
        query = QueryBuilder.build_combined_search(text, user_id, pagination, sort_by)
        res = self._execute_search(query)
        if res is None:
            return None
        return self._extract_search_result(res, pagination)
    
    def search_with_date_range(
        self,
        text: str,
        user_id: str,
        start_date: str,
        end_date: str,
        size: int = DEFAULT_PAGE_SIZE
    ) -> Optional[SearchResult]:
        """
        Search prescriptions by medicine name within a date range.
        
        Args:
            text: Medicine name to search for
            user_id: User ID to filter results
            start_date: Start date in ISO format (inclusive)
            end_date: End date in ISO format (inclusive)
            size: Maximum number of results to return
        
        Returns:
            Elasticsearch search results or None if disabled/unavailable
        """
        query = QueryBuilder.build_date_range_search(
            text, user_id, start_date, end_date, size
        )
        res = self._execute_search(query)
        if res is None:
            return None
        return self._extract_search_result(res)
    
    def autocomplete_search(
        self,
        text: str,
        user_id: str,
        size: int = DEFAULT_PAGE_SIZE
    ) -> Optional[SearchResult]:
        """
        Autocomplete search with exact match priority.
        
        Args:
            text: Partial text for autocomplete
            user_id: User ID to filter results
            size: Maximum number of suggestions
        
        Returns:
            Elasticsearch search results or None if disabled/unavailable
        """
        query = QueryBuilder.build_autocomplete_search(text, user_id, size)
        res = self._execute_search(query)
        if res is None:
            return None
        return self._extract_search_result(res)
    
    def fuzzy_search(
        self,
        text: str,
        user_id: str,
        page: int = 1,
        page_size: int = DEFAULT_PAGE_SIZE,
        sort_by: str = "relevance"
    ) -> Optional[SearchResult]:
        """
        Fuzzy search with safe tuning to prevent wild matches.
        
        Args:
            text: Search text (handles typos)
            user_id: User ID to filter results
            page: Page number for pagination
            page_size: Results per page
            sort_by: Sort by 'relevance' or 'date'
        
        Returns:
            Elasticsearch search results or None if disabled/unavailable
        """
        pagination = PaginationParams(page=page, page_size=page_size)
        query = QueryBuilder.build_fuzzy_search(text, user_id, pagination, sort_by)
        res = self._execute_search(query)
        if res is None:
            return None
        return self._extract_search_result(res, pagination)
    
    def delete_prescription(self, prescription_id: str) -> bool:
        """
        Delete a prescription from Elasticsearch index.
        
        Args:
            prescription_id: ID of the prescription to delete
        
        Returns:
            True if deletion was successful, False otherwise
        """
        if not self._is_enabled():
            logger.debug(
                f"Elasticsearch deletion skipped for prescription {prescription_id} "
                "(disabled)"
            )
            return False
        
        # Explicit None check for type safety
        if self._client is None:
            return False
        
        try:
            from elastic_transport import ConnectionError as ESConnectionError
            
            self._client.delete(index=self._index_alias, id=prescription_id)
            # The instruction implies an indices.delete call, but the context is deleting a document.
            # If an indices.delete call were to be added, it would look like this:
            # self._client.indices.delete(index=self._new_index, ignore_unavailable=True, refresh='wait_for')
            logger.info(
                f"Successfully deleted prescription {prescription_id} from Elasticsearch"
            )
            return True
            
        except ESConnectionError as e:
            logger.warning(
                f"Elasticsearch connection failed for prescription {prescription_id} "
                f"deletion. Error: {e}"
            )
            return False
        except Exception as e:
            logger.error(
                f"Unexpected error deleting prescription {prescription_id} "
                f"from Elasticsearch: {e}"
            )
            return False
    
    def semantic_search(
        self,
        query: str,
        user_id: str,
        query_vector: list,
        size: int = 10
    ) -> Optional[SearchResult]:
        """
        Production Semantic Search (HNSW pure vector search).
        
        Args:
            query: Search query text (used for logging if needed)
            user_id: User ID for filtering (security)
            query_vector: Embedding vector for semantic search
            size: Maximum number of results
            
        Returns:
            Elasticsearch search results or None if disabled/unavailable
        """
        if not self._is_enabled():
            logger.debug("Elasticsearch semantic search skipped (disabled)")
            return None
        
        # Explicit None check for type safety
        if self._client is None:
            return None
        
        # Use the configured alias/index
        index_name = getattr(settings, 'ES_INDEX_ALIAS', "prescriptions_current")
        
        query_body = QueryBuilder.build_semantic_search(
            user_id=user_id,
            query_vector=query_vector,
            size=size
        )
        
        try:
            res = self._client.search(index=index_name, body=query_body)
            return self._extract_search_result(res)
        except Exception as e:
            logger.error(f"Semantic search failed: {e}")
            return None

    def hybrid_search(
        self,
        query: str,
        user_id: str,
        query_vector: list,
        size: int = 5
    ) -> Optional[SearchResult]:
        """
        Production Hybrid Search: BM25 + HNSW + Script Scoring.
        
        Uses script_score with cosineSimilarity to combine:
        - BM25 lexical matching (_score from bool query)
        - Vector semantic matching (cosineSimilarity with HNSW index)
        
        The final score is a weighted combination controlled by:
        - ES_HYBRID_ALPHA (default 0.5) - BM25 weight
        - ES_HYBRID_BETA (default 0.5) - Vector weight
        
        Args:
            query: Search query text
            user_id: User ID for filtering (security)
            query_vector: Embedding vector for semantic search
            size: Maximum number of results
            
        Returns:
            Elasticsearch search results or None if disabled/unavailable
            
        Note:
            Hybrid ranking requires:
            - Documents contain the 'embedding_vector' field
            - Dimensions match between query and stored embeddings
            - Vector indexing is enabled (HNSW) in the index mapping
        """
        if not self._is_enabled():
            logger.debug("Elasticsearch hybrid search skipped (disabled)")
            return None
        
        # Explicit None check for type safety
        if self._client is None:
            return None
        
        # Use the configured alias/index for hybrid search
        index_name = getattr(settings, 'ES_INDEX_ALIAS', "prescriptions_current")
        
        # Build the query as a Python dict (avoiding JSON string issues)
        query_body = QueryBuilder.build_hybrid_search(
            query=query,
            user_id=user_id,
            query_vector=query_vector,
            size=size
        )
        
        try:
            res = self._client.search(index=index_name, body=query_body)
            return self._extract_search_result(res)
        except Exception as e:
            logger.error(f"Hybrid search failed: {e}")
            return None


# ============================================================================
# Asynchronous Service
# ============================================================================


class AsyncSearchService:
    """
    Asynchronous Elasticsearch service for prescription search operations.
    
    This service provides non-blocking operations for indexing and searching
    prescription documents with retry protection.
    """
    
    def __init__(self, client: Optional[Any] = None):
        """
        Initialize the async search service.
        
        Args:
            client: Optional AsyncElasticsearch client. If not provided,
                   will get from factory.
        """
        self._explicit_client = client
        # Use the same index alias as SyncSearchService for consistency
        self._index_name = getattr(settings, 'ES_INDEX_ALIAS', "prescriptions_current")
        self._write_index = getattr(settings, 'ES_WRITE_INDEX', "prescriptions-prod-write")

    @property
    def _client(self):
        return self._explicit_client or ElasticsearchClientFactory.get_async_client()

    def _extract_search_result(self, result: Dict[str, Any], pagination: Optional[PaginationParams] = None) -> SearchResult:
        """
        Extract standardized search results from raw Elasticsearch response.
        
        Handles:
        - Numeric casting for took_ms and total counts
        - hits extraction
        - pagination metadata
        """
        hits = result.get("hits", {})
        total_info = hits.get("total", {})
        total_count = total_info.get("value", 0) if isinstance(total_info, dict) else total_info
        
        return SearchResult(
            hits=hits.get("hits", []),
            total=int(total_count),
            page=pagination.page if pagination else 1,
            page_size=pagination.page_size if pagination else len(hits.get("hits", [])),
            took_ms=int(result.get("took", 0))
        )

    def get_async_client(self):
        """Get the underlying async Elasticsearch client."""
        return self._client
    
    async def close(self) -> None:
        """Close the async client connection."""
        if self._client is not None:
            await self._client.close()
            ElasticsearchClientFactory._async_client = None
    
    async def health_check(self) -> bool:
        """
        Check Elasticsearch cluster health.
        
        Supports both API key and basic authentication.
        
        Returns:
            True if cluster is healthy, False otherwise
        """
        import aiohttp
        import base64
        
        try:
            # Prepare headers and auth based on configuration
            headers = {"Accept": "application/json"}
            
            if settings.ES_API_KEY:
                # Use API key authentication
                # API key format: "id.api_key" - already base64 encoded by Elasticsearch
                # The encoded format is what should be used directly in the header
                headers["Authorization"] = f"ApiKey {settings.ES_API_KEY}"
                auth = None
                logger.debug("AsyncSearchService: Using API key authentication for health check")
            else:
                # Use basic authentication
                auth = aiohttp.BasicAuth(settings.ES_USER, settings.ES_PASS)
                logger.debug("AsyncSearchService: Using basic authentication for health check")
            
            # Use direct HTTP check instead of client methods to avoid library issues
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{settings.ES_HOST}/_cluster/health",
                    headers=headers,
                    auth=auth,
                    timeout=aiohttp.ClientTimeout(total=5),
                    ssl=False
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        cluster_status = data.get('status', 'unknown')
                        # Consider green or yellow as healthy
                        return cluster_status in ('green', 'yellow')
                    elif response.status == 401:
                        logger.warning("AsyncSearchService: Elasticsearch authentication failed (401). Check ES_API_KEY or ES_USER/ES_PASS.")
                        return False
                    else:
                        logger.warning(f"AsyncSearchService: Elasticsearch health check returned status: {response.status}")
                        return False
                    
        except aiohttp.ClientConnectorError as e:
            logger.warning(f"Cannot connect to Elasticsearch: {e}")
            return False
        except Exception as e:
            logger.warning(f"Elasticsearch health check failed: {e}")
            return False
        
        return False
    
    async def create_index_if_not_exists(self) -> None:
        """
        Create Elasticsearch index with proper mappings for hybrid search.
        
        Production Index Configuration:
        ├── BM25 fields: medicine_names, diagnosis, raw_text (text)
        ├── user_id: keyword (for filtering)
        └── embedding_vector: dense_vector with HNSW (semantic search)
        
        Safe to call multiple times.
        
        Note: This requires 'create_index' privilege. If using a restricted user,
        create the index manually as the elastic superuser first.
        """
        if self._client is None:
            logger.debug("Elasticsearch index creation skipped (disabled)")
            return
        
        try:
            exists = await self._client.indices.exists(index=self._index_name)
            if exists:
                logger.debug(f"Index '{self._index_name}' already exists")
                return
            
            # Get vector dimensions from settings
            vector_dims = getattr(settings, 'ES_VECTOR_DIMS', 768)
            
            # Load synonyms inline to avoid Docker volume mount requirements
            import os
            from pathlib import Path
            synonyms_list = []
            try:
                # Find the synonyms file relative to the project root
                synonyms_path = Path(__file__).parent.parent.parent.parent / "analysis" / "medical_synonyms.txt"
                if synonyms_path.exists():
                    with open(synonyms_path, "r", encoding="utf-8") as f:
                        synonyms_list = [line.strip() for line in f if line.strip() and not line.startswith("#")]
                else:
                    logger.warning(f"Medical synonyms file not found at {synonyms_path}")
            except Exception as e:
                logger.error(f"Error loading medical synonyms: {e}")
                
            mapping = {
                "settings": {
                    "number_of_shards": 1,
                    "analysis": {
                        "filter": {
                            "medical_synonym_filter": {
                                "type": "synonym_graph",
                                "synonyms": synonyms_list if synonyms_list else ["dummy=>dummy"]
                            }
                        },
                        "analyzer": {
                            "english_custom": {
                                "type": "standard",
                                "stopwords": "_english_"
                            },
                            "lowercase_analyzer": {
                                "type": "custom",
                                "tokenizer": "standard",
                                "filter": ["lowercase"]
                            },
                            "medical_analyzer": {
                                "type": "custom",
                                "tokenizer": "standard",
                                "filter": ["lowercase", "medical_synonym_filter"]
                            }
                        }
                    }
                },
                "mappings": {
                    "properties": {
                        "prescription_id": {"type": "keyword"},
                        "user_id": {"type": "keyword"},  # Required for filtering
                        "doctor_name": {"type": "search_as_you_type"},
                        "hospital": {"type": "search_as_you_type"},
                        "medicine_names": {
                            "type": "search_as_you_type",
                            "fields": {
                                "synonym": {
                                    "type": "text",
                                    "analyzer": "medical_analyzer"
                                }
                            }
                        },
                        "diagnosis": {
                            "type": "text",
                            "analyzer": "medical_analyzer"
                        },
                        "raw_text": {
                            "type": "text",
                            "analyzer": "medical_analyzer"
                        },
                        "medicines": {
                            "type": "nested",
                            "properties": {
                                "name": {"type": "search_as_you_type"}
                            }
                        },
                        "created_at": {"type": "date"},
                        # int8_hnsw Vector Index for Production Semantic Search
                        "embedding_vector": {
                            "type": "dense_vector",
                            "dims": vector_dims,
                            "index": True,
                            "similarity": "cosine",
                            "index_options": {
                                "type": "int8_hnsw",
                                "m": 16,
                                "ef_construction": 100
                            }
                        }
                    }
                }
            }
            
            await self._client.indices.create(
                index=self._index_name,
                body=mapping
            )
            logger.info(f"Elasticsearch index '{self._index_name}' created")
            
        except Exception as e:
            error_msg = str(e)
            if "403" in error_msg or "AuthorizationException" in error_msg:
                logger.warning(
                    f"Cannot create index '{self._index_name}': Permission denied. "
                    f"The restricted user lacks 'create_index' privilege. "
                    f"Create the index manually as the elastic superuser: "
                    f"curl -u elastic:YOUR_PASSWORD -X PUT http://localhost:9200/{self._index_name}"
                )
                # Don't raise - index might already exist or will be created by admin
                return
            logger.error(f"Failed to create Elasticsearch index: {e}")
            raise IndexError(f"Failed to create index: {e}") from e
    
    async def index_document(self, prescription_id: str, doc: Dict[str, Any]) -> None:
        """Alias for index_prescription for generic document indexing."""
        await self.index_prescription(prescription_id, doc)

    @retry(
        stop=stop_after_attempt(MAX_RETRIES),
        wait=wait_exponential(multiplier=1, min=RETRY_WAIT_MIN, max=RETRY_WAIT_MAX)
    )
    async def index_prescription(self, prescription_id: str, doc: Dict[str, Any]) -> None:
        """
        Index a document with retry protection.
        
        Args:
            prescription_id: Unique identifier for the prescription
            doc: Document data to index
        
        Raises:
            IndexError: If indexing fails after all retries
        """
        if self._client is None:
            raise IndexError("Elasticsearch is disabled")
        
        try:
            from datetime import datetime, timezone
            
            doc["created_at"] = datetime.now(timezone.utc).isoformat()
            
            await self._client.index(
                index=self._write_index,
                id=prescription_id,
                document=doc
            )
        except Exception as e:
            logger.error(f"Failed to index document {prescription_id}: {e}")
            raise IndexError(f"Indexing failed: {e}") from e
    
    @log_performance("Service: Search By Medicine")
    async def search_medicine(
        self,
        query: str,
        user_id: str,
        size: int = DEFAULT_PAGE_SIZE
    ) -> Optional[SearchResult]:
        """
        Search for medicines using production-grade nested querying.
        
        Args:
            query: Search query text
            user_id: User ID to filter results
            size: Maximum number of results
        
        Returns:
            Search results or None if disabled/error
        """
        if self._client is None:
            logger.debug("Elasticsearch search skipped (disabled)")
            return None
        
        body = QueryBuilder.build_nested_medicine_query(query, user_id, size)
        
        try:
            res = await self._client.search(
                index=self._index_name,  # Uses the read alias
                body=body
            )
            return self._extract_search_result(res)
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return None

    @log_performance("Service: Search By Provider")
    async def search_by_doctor_or_hospital(
        self,
        query_text: str,
        user_id: str,
        size: int = DEFAULT_PAGE_SIZE
    ) -> Optional[SearchResult]:
        """
        Search prescriptions by doctor name or hospital (Asynchronous).
        """
        if self._client is None:
            return None
        
        body = QueryBuilder.build_doctor_hospital_search(query_text, user_id, size)
        
        try:
            res = await self._client.search(
                index=self._index_name,
                body=body
            )
            return self._extract_search_result(res)
        except Exception as e:
            logger.error(f"Doctor/Hospital search failed: {e}")
            return None

    @log_performance("Service: Search All")
    async def search_all(
        self,
        text: str,
        user_id: str,
        page: int = 1,
        page_size: int = DEFAULT_PAGE_SIZE,
        sort_by: str = "relevance"
    ) -> Optional[SearchResult]:
        """
        Advanced search with exact match priority and recency boost (Asynchronous).
        """
        if self._client is None:
            return None
        
        pagination = PaginationParams(page=page, page_size=page_size)
        body = QueryBuilder.build_combined_search(text, user_id, pagination, sort_by)
        
        try:
            res = await self._client.search(
                index=self._index_name,
                body=body
            )
            return self._extract_search_result(res, pagination)
        except Exception as e:
            logger.error(f"Search all failed: {e}")
            return None

    @log_performance("Service: Search Date Range")
    async def search_with_date_range(
        self,
        text: str,
        user_id: str,
        start_date: str,
        end_date: str,
        size: int = DEFAULT_PAGE_SIZE
    ) -> Optional[SearchResult]:
        """
        Search prescriptions by medicine name within a date range (Asynchronous).
        """
        if self._client is None:
            return None
        
        body = QueryBuilder.build_date_range_search(text, user_id, start_date, end_date, size)
        
        try:
            res = await self._client.search(
                index=self._index_name,
                body=body
            )
            return self._extract_search_result(res)
        except Exception as e:
            logger.error(f"Date range search failed: {e}")
            return None

    async def autocomplete(self, query: str, user_id: str, size: int = 5) -> Optional[SearchResult]:
        """Alias for autocomplete_search."""
        return await self.autocomplete_search(query, user_id, size)

    @log_performance("Service: Autocomplete Search")
    async def autocomplete_search(
        self,
        query: str,
        user_id: str,
        size: int = 5
    ) -> Optional[SearchResult]:
        """
        Production-grade multi-field autocomplete using hardened query patterns (Asynchronous).
        """
        if self._client is None:
            return None
        
        body = QueryBuilder.build_autocomplete_search(query, user_id, size)
        
        try:
            res = await self._client.search(
                index=self._index_name,
                body=body
            )
            return self._extract_search_result(res)
        except Exception as e:
            logger.error(f"Autocomplete search failed: {e}")
            return None

    @log_performance("Service: Fuzzy Search")
    async def fuzzy_search(
        self,
        text: str,
        user_id: str,
        page: int = 1,
        page_size: int = DEFAULT_PAGE_SIZE,
        sort_by: str = "relevance"
    ) -> Optional[SearchResult]:
        """
        Fuzzy search with safe tuning to prevent wild matches (Asynchronous).
        """
        if self._client is None:
            return None
        
        pagination = PaginationParams(page=page, page_size=page_size)
        body = QueryBuilder.build_fuzzy_search(text, user_id, pagination, sort_by)
        
        try:
            res = await self._client.search(
                index=self._index_name,
                body=body
            )
            return self._extract_search_result(res, pagination)
        except Exception as e:
            logger.error(f"Fuzzy search failed: {e}")
            return None

    async def delete_prescription(self, prescription_id: str) -> bool:
        """
        Delete a prescription from Elasticsearch index (Asynchronous).
        """
        if self._client is None:
            return False
        
        try:
            await self._client.delete(
                index=self._write_index,
                id=prescription_id,
                refresh='wait_for'
            )
            return True
        except Exception as e:
            logger.warning(f"Failed to delete document {prescription_id}: {e}")
            return False
    
    @log_performance("Service: Semantic Search")
    async def semantic_search(
        self,
        query: str,
        user_id: str,
        query_vector: list,
        size: int = 10
    ) -> Optional[SearchResult]:
        """
        Production Semantic Search (HNSW pure vector search).
        """
        if self._client is None:
            logger.debug("Elasticsearch semantic search skipped (disabled)")
            return None
        
        body = QueryBuilder.build_semantic_search(
            user_id=user_id,
            query_vector=query_vector,
            size=size
        )
        
        try:
            res = await self._client.search(
                index=self._index_name,  # Uses the read alias
                body=body
            )
            return self._extract_search_result(res)
        except Exception as e:
            logger.error(f"Semantic search failed: {e}")
            return None

    @log_performance("Service: Hybrid Search")
    async def hybrid_search(
        self,
        query: str,
        user_id: str,
        query_vector: list,
        size: int = 5
    ) -> Optional[SearchResult]:
        """
        Level 3 Hybrid search combining lexical and semantic matching.
        """
        if self._client is None:
            logger.debug("Elasticsearch hybrid search skipped (disabled)")
            return None
        
        body = QueryBuilder.build_hybrid_search(
            query=query,
            user_id=user_id,
            query_vector=query_vector,
            size=size
        )
        
        try:
            res = await self._client.search(
                index=self._index_name,  # Uses the read alias
                body=body
            )
            return self._extract_search_result(res)
        except Exception as e:
            logger.error(f"Hybrid search failed: {e}")
            return None


# ============================================================================
# Query Builder for Autocomplete Strategies
# ============================================================================


class AutocompleteQueryBuilder:
    """Builder for autocomplete queries with different strategies."""
    
    @staticmethod
    def build_prefix_only_query(query: str, user_id: str, size: int) -> Dict[str, Any]:
        """
        Build prefix-only autocomplete query (fast).
        
        Uses bool_prefix for as-you-type completion.
        """
        return {
            "size": size,
            "_source": [
                "prescription_id",
                "medicine_names",
                "doctor_name",
                "hospital"
            ],
            "query": {
                "bool": {
                    "must": [
                        {
                            "multi_match": {
                                "query": query,
                                "type": "bool_prefix",
                                "fields": [
                                    "medicine_names^4",
                                    "medicine_names._2gram^3",
                                    "medicine_names._3gram^3",
                                    "doctor_name^2",
                                    "hospital"
                                ]
                            }
                        }
                    ],
                    "filter": [
                        {"term": {"user_id": user_id}}
                    ]
                }
            }
        }
    
    @staticmethod
    def build_prefix_fuzzy_query(query: str, user_id: str, size: int) -> Dict[str, Any]:
        """
        Build prefix + fuzzy autocomplete query (comprehensive).
        
        Combines bool_prefix matching with fuzzy matching for better recall.
        """
        return {
            "size": size,
            "_source": [
                "prescription_id",
                "medicine_names",
                "doctor_name",
                "hospital"
            ],
            "query": {
                "bool": {
                    "should": [
                        # Prefix matching (bool_prefix)
                        {
                            "multi_match": {
                                "query": query,
                                "type": "bool_prefix",
                                "fields": [
                                    "medicine_names^4",
                                    "medicine_names._2gram^3",
                                    "medicine_names._3gram^3",
                                    "doctor_name^2",
                                    "hospital"
                                ]
                            }
                        },
                        # Fuzzy matching for typo tolerance
                        {
                            "multi_match": {
                                "query": query,
                                "fields": [
                                    "medicine_names^2",
                                    "doctor_name",
                                    "hospital"
                                ],
                                "fuzziness": "AUTO",
                                "prefix_length": 1,
                                "max_expansions": 30
                            }
                        }
                    ],
                    "filter": [
                        {"term": {"user_id": user_id}}
                    ],
                    "minimum_should_match": 1
                }
            }
        }
    
    @classmethod
    def build_query(
        cls,
        query: str,
        user_id: str,
        size: int,
        strategy: SearchStrategy = SearchStrategy.PREFIX_FUZZY
    ) -> Dict[str, Any]:
        """
        Build autocomplete query based on strategy.
        
        Args:
            query: Search query text
            user_id: User ID for filtering
            size: Maximum results
            strategy: Search strategy (prefix or prefix_fuzzy)
        
        Returns:
            Elasticsearch query body
        """
        if strategy == SearchStrategy.PREFIX_ONLY:
            return cls.build_prefix_only_query(query, user_id, size)
        else:
            return cls.build_prefix_fuzzy_query(query, user_id, size)


class IndexMigrationManager:
    """Manager for Elasticsearch index migrations with zero downtime."""
    
    def __init__(self, client: Optional[ElasticsearchClient] = None):
        """
        Initialize the migration manager.
        
        Args:
            client: Optional Elasticsearch client
        """
        self._client = client or ElasticsearchClientFactory.get_sync_client()
        self._alias_name = getattr(settings, 'ES_INDEX_ALIAS', "prescriptions_current")
    
    def _is_enabled(self) -> bool:
        """Check if Elasticsearch is enabled."""
        return self._client is not None
    
    def create_versioned_index(self, version: str) -> Optional[str]:
        """
        Create a new versioned index with proper mappings.
        
        Args:
            version: Version string for the index name
        
        Returns:
            Index name if created, None if already exists or disabled
        """
        if not self._is_enabled():
            return None
        
        # Explicit None check for type safety
        if self._client is None:
            return None
        
        index_name = f"prescriptions_{version}"
        
        # Get indices client with proper typing
        indices_client: IndicesClient = self._client.indices
        
        # Check if index already exists
        try:
            if indices_client.exists(index=index_name):
                return index_name
        except Exception as e:
            logger.error(f"Failed to check index existence: {e}")
            return None
        
        # Load synonyms inline to avoid Docker volume mount requirements
        import os
        from pathlib import Path
        synonyms_list = []
        try:
            # Find the synonyms file relative to the project root
            synonyms_path = Path(__file__).parent.parent.parent.parent / "analysis" / "medical_synonyms.txt"
            if synonyms_path.exists():
                with open(synonyms_path, "r", encoding="utf-8") as f:
                    synonyms_list = [line.strip() for line in f if line.strip() and not line.startswith("#")]
            else:
                logger.warning(f"Medical synonyms file not found at {synonyms_path}")
        except Exception as e:
            logger.error(f"Error loading medical synonyms: {e}")

        index_body = {
            "settings": {
                "number_of_shards": 1,
                "analysis": {
                    "filter": {
                        "medical_synonym_filter": {
                            "type": "synonym_graph",
                            "synonyms": synonyms_list if synonyms_list else ["dummy=>dummy"]
                        }
                    },
                    "analyzer": {
                        "english_custom": {
                            "type": "standard",
                            "stopwords": "_english_"
                        },
                        "lowercase_analyzer": {
                            "type": "custom",
                            "tokenizer": "standard",
                            "filter": ["lowercase"]
                        },
                        "medical_analyzer": {
                            "type": "custom",
                            "tokenizer": "standard",
                            "filter": ["lowercase", "medical_synonym_filter"]
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
                    "medicine_names": {
                        "type": "search_as_you_type",
                        "fields": {
                            "synonym": {
                                "type": "text",
                                "analyzer": "medical_analyzer"
                            }
                        }
                    },
                    "diagnosis": {
                        "type": "text",
                        "analyzer": "medical_analyzer"
                    },
                    "raw_text": {
                        "type": "text",
                        "analyzer": "medical_analyzer"
                    },
                    "medicines": {
                        "type": "nested",
                        "properties": {
                            "name": {"type": "search_as_you_type"}
                        }
                    },
                    "created_at": {"type": "date"},
                    # FIX: Standardized on int8_hnsw for production performance
                    "embedding_vector": {
                        "type": "dense_vector",
                        "dims": settings.ES_VECTOR_DIMS,
                        "index": True,
                        "similarity": "cosine",
                        "index_options": {
                            "type": "int8_hnsw",
                            "m": 16,
                            "ef_construction": 100
                        }
                    }
                }
            }
        }
        
        try:
            indices_client.create(index=index_name, body=index_body)
            logger.info(f"Created index: {index_name}")
            return index_name
        except Exception as e:
            logger.error(f"Failed to create index {index_name}: {e}")
            return None
    
    def reindex_data(self, old_index: str, new_index: str) -> bool:
        """
        Reindex data from old index to new index.
        
        Args:
            old_index: Source index name
            new_index: Target index name
        
        Returns:
            True if reindexing succeeded, False otherwise
        """
        if not self._is_enabled():
            return False
        
        # Explicit None check for type safety
        if self._client is None:
            return False
        
        body = {
            "source": {"index": old_index},
            "dest": {"index": new_index}
        }
        
        try:
            self._client.reindex(body=body, wait_for_completion=True)
            logger.info(f"Reindexed from {old_index} to {new_index}")
            return True
        except Exception as e:
            logger.error(f"Reindexing failed: {e}")
            return False
    
    def verify_reindex(self, old_index: str, new_index: str) -> bool:
        """
        Verify that reindex completed successfully by comparing document counts.
        
        Args:
            old_index: Source index name
            new_index: Target index name
        
        Returns:
            True if counts match, False otherwise
        
        Raises:
            RuntimeError: If new index has fewer documents than old index
        """
        if not self._is_enabled():
            return False
        
        # Explicit None check for type safety
        if self._client is None:
            return False
        
        try:
            old_count = self._client.count(index=old_index)["count"]
            new_count = self._client.count(index=new_index)["count"]
            
            if new_count < old_count:
                raise RuntimeError(
                    f"Reindex incomplete: {new_count} < {old_count} documents"
                )
            
            logger.info(
                f"Reindex verified: {old_count} documents in both indices"
            )
            return True
            
        except RuntimeError:
            raise
        except Exception as e:
            logger.error(f"Failed to verify reindex: {e}")
            return False
    
    def switch_alias_atomically(self, new_index: str) -> bool:
        """
        Atomically switch alias to new index for zero downtime.
        
        Args:
            new_index: New index to point alias to
        
        Returns:
            True if switch succeeded, False otherwise
        """
        if not self._is_enabled():
            return False
        
        # Explicit None check for type safety
        if self._client is None:
            return False
        
        # Get indices client with proper typing
        indices_client: IndicesClient = self._client.indices
        
        actions: List[Dict[str, Any]] = []
        
        # Remove alias from any existing indices
        try:
            current = indices_client.get_alias(name=self._alias_name)
            for idx in current.keys():
                actions.append({
                    "remove": {
                        "index": idx,
                        "alias": self._alias_name
                    }
                })
        except Exception:
            # Alias doesn't exist yet, which is fine
            pass
        
        # Add alias to new index
        actions.append({
            "add": {
                "index": new_index,
                "alias": self._alias_name
            }
        })
        
        try:
            indices_client.update_aliases(body={"actions": actions})
            logger.info(f"Switched alias '{self._alias_name}' to index '{new_index}'")
            return True
        except Exception as e:
            logger.error(f"Failed to switch alias: {e}")
            return False


# ============================================================================
# Convenience Functions (Legacy API)
# ============================================================================

# Global service instances for backward compatibility
_sync_service: Optional[SyncSearchService] = None
_async_service: Optional[AsyncSearchService] = None


def _get_sync_service() -> Optional[SyncSearchService]:
    """Get or create sync service singleton."""
    global _sync_service
    if _sync_service is None:
        _sync_service = SyncSearchService()
    return _sync_service


def _get_async_service() -> Optional[AsyncSearchService]:
    """Get or create async service singleton."""
    global _async_service
    if _async_service is None:
        _async_service = AsyncSearchService()
    return _async_service


# Legacy function wrappers for backward compatibility
async def index_prescription(
    prescription_id: str,
    data: Dict[str, Any],
    user_id: Optional[str] = None
) -> bool:
    """Legacy wrapper for AsyncSearchService.index_prescription."""
    service = _get_async_service()
    if service is None:
        return False
    # index_prescription in AsyncSearchService returns None but raises on error
    try:
        await service.index_prescription(prescription_id, data)
        return True
    except Exception:
        return False


async def search_by_medicine(
    medicine: str,
    user_id: str,
    size: int = DEFAULT_PAGE_SIZE
) -> Optional[SearchResult]:
    """Legacy wrapper for AsyncSearchService.search_medicine."""
    service = _get_async_service()
    if service is None:
        return None
    return await service.search_medicine(medicine, user_id, size)


async def search_by_doctor_or_hospital(
    query_text: str,
    user_id: str,
    size: int = DEFAULT_PAGE_SIZE
) -> Optional[SearchResult]:
    """Legacy wrapper for AsyncSearchService.search_by_doctor_or_hospital."""
    service = _get_async_service()
    if service is None:
        return None
    return await service.search_by_doctor_or_hospital(query_text, user_id, size)


async def search_all(
    text: str,
    user_id: str,
    page: int = 1,
    page_size: int = DEFAULT_PAGE_SIZE,
    sort_by: str = "relevance"
) -> Optional[SearchResult]:
    """Legacy wrapper for AsyncSearchService.search_all."""
    service = _get_async_service()
    if service is None:
        return None
    return await service.search_all(text, user_id, page, page_size, sort_by)


async def search_with_date_range(
    text: str,
    user_id: str,
    start_date: str,
    end_date: str,
    size: int = DEFAULT_PAGE_SIZE
) -> Optional[SearchResult]:
    """Legacy wrapper for AsyncSearchService.search_with_date_range."""
    service = _get_async_service()
    if service is None:
        return None
    return await service.search_with_date_range(text, user_id, start_date, end_date, size)


async def autocomplete_search(
    text: str,
    user_id: str,
    size: int = DEFAULT_PAGE_SIZE
) -> Optional[SearchResult]:
    """Legacy wrapper for AsyncSearchService.autocomplete_search."""
    service = _get_async_service()
    if service is None:
        return None
    return await service.autocomplete_search(text, user_id, size)


async def fuzzy_search(
    text: str,
    user_id: str,
    page: int = 1,
    page_size: int = DEFAULT_PAGE_SIZE,
    sort_by: str = "relevance"
) -> Optional[SearchResult]:
    """Legacy wrapper for AsyncSearchService.fuzzy_search."""
    service = _get_async_service()
    if service is None:
        return None
    return await service.fuzzy_search(text, user_id, page, page_size, sort_by)


async def delete_prescription(prescription_id: str) -> bool:
    """Legacy wrapper for AsyncSearchService.delete_prescription."""
    service = _get_async_service()
    if service is None:
        return False
    return await service.delete_prescription(prescription_id)


def create_prescriptions_index(version: str) -> Optional[str]:
    """Legacy wrapper for IndexMigrationManager.create_versioned_index."""
    manager = IndexMigrationManager()
    return manager.create_versioned_index(version)


def reindex_prescriptions(old_index: str, new_index: str) -> bool:
    """Legacy wrapper for IndexMigrationManager.reindex_data."""
    manager = IndexMigrationManager()
    return manager.reindex_data(old_index, new_index)


def switch_alias_to_new_index(new_index: str) -> bool:
    """Legacy wrapper for IndexMigrationManager.switch_alias_atomically."""
    manager = IndexMigrationManager()
    return manager.switch_alias_atomically(new_index)


def verify_reindex(old_index: str, new_index: str) -> bool:
    """Legacy wrapper for IndexMigrationManager.verify_reindex."""
    manager = IndexMigrationManager()
    return manager.verify_reindex(old_index, new_index)


# ============================================================================
# Singleton Exports
# ============================================================================

# Keep the old es_service singleton for full backward compatibility
class ElasticsearchService(AsyncSearchService):
    """
    Backward-compatible wrapper around AsyncSearchService.
    
    Maintains the same interface as the original ElasticsearchService class.
    """
    pass


# Create singleton instance
es_service = ElasticsearchService()