from elasticsearch import Elasticsearch
import os

ES_HOST = os.getenv("ELASTICSEARCH_HOST", "http://localhost:9200")
ES_INDEX = "prescriptions"

es = Elasticsearch(ES_HOST)

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
