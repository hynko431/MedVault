import logging
from typing import Optional
from elasticsearch import Elasticsearch
from elastic_transport import ConnectionError as ESConnectionError
from app.core.config import settings

logger = logging.getLogger(__name__)

ES_INDEX = "prescriptions"

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


def index_prescription(prescription_id: str, data: dict) -> bool:
    """
    Index prescription data to Elasticsearch.
    
    Returns True if indexing was successful, False otherwise.
    Gracefully handles connection errors without crashing the application.
    """
    es = get_es_client()
    
    if es is None:
        logger.debug(
            f"Elasticsearch indexing skipped for prescription {prescription_id} "
            "(ELASTICSEARCH_ENABLED=false)"
        )
        return False
    
    document = {
        "prescription_id": prescription_id,
        "doctor_name": data.get("doctor_name"),
        "hospital": data.get("hospital"),
        "medicines": [
            med.get("name") for med in data.get("medicines", [])
        ]
    }

    try:
        es.index(index=ES_INDEX, id=prescription_id, document=document)
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
