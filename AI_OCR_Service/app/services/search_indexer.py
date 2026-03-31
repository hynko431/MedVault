import logging
from elasticsearch import Elasticsearch, ConnectionError as ESConnectionError
from app.core.config import settings

logger = logging.getLogger(__name__)

# Lazy singleton — only created on first use, not at import time.
_es_client: Elasticsearch | None = None


def get_es_client() -> Elasticsearch:
    """Return a cached Elasticsearch client, initializing it on first call."""
    global _es_client
    if _es_client is None:
        _es_client = Elasticsearch(settings.ELASTICSEARCH_HOST)
    return _es_client


def index_prescription(prescription_id: str, data: dict) -> None:
    """
    Index a fully structured prescription document into Elasticsearch.
    Errors are logged but do NOT propagate — OCR results must never be
    lost because of an ES outage.
    """
    try:
        es = get_es_client()

        document = {
            "prescription_id": prescription_id,
            "doctor_name": data.get("doctor_name"),
            "hospital": data.get("hospital"),
            "patient_name": data.get("patient_name"),
            "date": data.get("date"),
            # Store full medicine objects, not just names
            "medicines": data.get("medicines", []),
            # Flat list of medicine names for easy full-text search
            "medicine_names": [
                med.get("name") for med in data.get("medicines", []) if med.get("name")
            ],
        }

        es.index(
            index=settings.ELASTICSEARCH_INDEX,
            id=prescription_id,
            document=document,
        )
        logger.info("Indexed prescription %s into Elasticsearch.", prescription_id)

    except ESConnectionError:
        logger.error(
            "Elasticsearch is unreachable. Prescription %s was NOT indexed.",
            prescription_id,
        )
    except Exception as e:
        logger.error(
            "Failed to index prescription %s: %s", prescription_id, str(e)
        )


def search_prescriptions(query: str, size: int = 10) -> list[dict]:
    """
    Full-text search across medicine names, doctor name, hospital, and patient name.
    Returns a list of matching documents.
    """
    try:
        es = get_es_client()

        body = {
            "size": size,
            "query": {
                "multi_match": {
                    "query": query,
                    "fields": [
                        "medicine_names^3",   # boost medicine name matches
                        "doctor_name",
                        "hospital",
                        "patient_name",
                    ],
                    "fuzziness": "AUTO",
                }
            },
        }

        response = es.search(index=settings.ELASTICSEARCH_INDEX, body=body)
        hits = response["hits"]["hits"]
        return [hit["_source"] for hit in hits]

    except ESConnectionError:
        logger.error("Elasticsearch is unreachable. Search returned empty.")
        return []
    except Exception as e:
        logger.error("Elasticsearch search error: %s", str(e))
        return []


def get_indexed_prescription(prescription_id: str) -> dict | None:
    """Fetch a single indexed prescription document by its ID."""
    try:
        es = get_es_client()
        response = es.get(index=settings.ELASTICSEARCH_INDEX, id=prescription_id)
        return response["_source"]
    except ESConnectionError:
        logger.error("Elasticsearch unreachable when fetching %s", prescription_id)
        return None
    except Exception:
        # Document not found or other error
        return None
