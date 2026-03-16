import requests
import json
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from app.core.config.config import settings

def migrate_to_strict_mapping():
    base_url = "http://localhost:9200"
    auth = ("elastic", "changeme123")
    headers = {"Content-Type": "application/json"}

    # 1. Define Template
    template_name = "prescriptions-template"
    template_payload = {
        "index_patterns": ["prescriptions-prod-*"],
        "priority": 200,
        "template": {
            "settings": {
                "number_of_shards": 1,
                "number_of_replicas": settings.ES_REPLICAS,
                "index.lifecycle.name": "prescriptions-ilm",
                "index.lifecycle.rollover_alias": "prescriptions-prod-write",
                "analysis": {
                    "analyzer": {
                        "english_custom": {
                            "type": "standard",
                            "stopwords": "_english_"
                        }
                    }
                }
            },
            "mappings": {
                "dynamic": "strict",
                "properties": {
                    "prescription_id": { "type": "keyword" },
                    "user_id": { "type": "keyword" },
                    "family_member_id": { "type": "keyword" },
                    "doctor_name": { "type": "search_as_you_type" },
                    "hospital": { "type": "search_as_you_type" },
                    "diagnosis": {
                        "type": "text",
                        "analyzer": "english_custom",
                        "fields": { "keyword": { "type": "keyword" } }
                    },
                    "raw_text": { "type": "text", "analyzer": "english_custom" },
                    "medicines": {
                        "type": "nested",
                        "properties": {
                            "name": {
                                "type": "search_as_you_type",
                                "fields": { "keyword": { "type": "keyword" } }
                            },
                            "dosage": { "type": "keyword" },
                            "frequency": { "type": "keyword" },
                            "duration": { "type": "keyword" },
                            "instructions": { "type": "text", "analyzer": "english_custom" }
                        }
                    },
                    "embedding_vector": {
                        "type": "dense_vector",
                        "dims": 768,
                        "index": True,
                        "similarity": "cosine"
                    },
                    "created_at": { "type": "date" },
                    "updated_at": { "type": "date" }
                }
            }
        }
    }

    print(f"--- Applying template: {template_name} ---")
    resp = requests.put(f"{base_url}/_index_template/{template_name}", auth=auth, headers=headers, json=template_payload)
    print(f"Status: {resp.status_code}, Response: {resp.text}")

    # 2. Create Next Index
    new_index = "prescriptions-prod-000002"
    print(f"\n--- Creating new index: {new_index} ---")
    resp = requests.put(f"{base_url}/{new_index}", auth=auth, headers=headers)
    print(f"Status: {resp.status_code}, Response: {resp.text}")

    # 3. Reindex
    source_index = "prescriptions-prod-000001"
    print(f"\n--- Reindexing from {source_index} to {new_index} ---")
    reindex_payload = {
        "source": { "index": source_index },
        "dest": { "index": new_index }
    }
    resp = requests.post(f"{base_url}/_reindex", auth=auth, headers=headers, json=reindex_payload)
    print(f"Status: {resp.status_code}, Response: {resp.text}")

    # 4. Atomic Alias Swap
    print("\n--- Performing Atomic Alias Swap ---")
    alias_payload = {
        "actions": [
            { "remove": { "index": source_index, "alias": "prescriptions-prod-write" }},
            { "add": { "index": new_index, "alias": "prescriptions-prod-write", "is_write_index": True }},
            { "remove": { "index": source_index, "alias": "prescriptions-prod-read" }},
            { "add": { "index": new_index, "alias": "prescriptions-prod-read" }}
        ]
    }
    resp = requests.post(f"{base_url}/_aliases", auth=auth, headers=headers, json=alias_payload)
    print(f"Status: {resp.status_code}, Response: {resp.text}")

if __name__ == "__main__":
    migrate_to_strict_mapping()
