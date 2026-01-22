from elasticsearch import Elasticsearch
from app.core.config import settings

ES_INDEX = "prescriptions"

es = Elasticsearch(settings.ELASTICSEARCH_HOST)

def index_prescription(prescription_id: str, data: dict):
    document = {
        "prescription_id": prescription_id,
        "doctor_name": data.get("doctor_name"),
        "hospital": data.get("hospital"),
        "medicines": [
            med.get("name") for med in data.get("medicines", [])
        ]
    }

    es.index(index=ES_INDEX, id=prescription_id, document=document)
