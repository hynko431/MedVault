import requests
import json
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from app.core.config.config import settings

def upgrade_to_v5_final_production():
    base_url = settings.ES_HOST
    auth = (settings.ES_USER, settings.ES_PASS)
    headers = {"Content-Type": "application/json"}

    # 1. Define Versioned Index Name
    new_index = "prescriptions_v5"
    alias_name = "prescriptions"

    # 2. Define Enterprise Mapping & Settings
    payload = {
        "settings": {
            "number_of_shards": 3,
            "number_of_replicas": 0,
            "refresh_interval": "1s",
            "analysis": {
                "filter": {
                    "medicine_synonyms": {
                        "type": "synonym",
                        "synonyms": [
                            "paracetamol, dolo, crocin",
                            "ibuprofen, brufen",
                            "pantoprazole, pan 40"
                        ]
                    }
                },
                "analyzer": {
                    "medicine_analyzer": {
                        "tokenizer": "standard",
                        "filter": [
                            "lowercase",
                            "asciifolding",
                            "medicine_synonyms"
                        ]
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

                # Pro-grade autocomplete
                "doctor_name": { "type": "search_as_you_type" },
                "hospital": { "type": "search_as_you_type" },
                "medicine_names": { "type": "search_as_you_type" },

                "diagnosis": {
                    "type": "text",
                    "analyzer": "medicine_analyzer",
                    "fields": { "keyword": { "type": "keyword" } }
                },

                "raw_text": {
                    "type": "text",
                    "analyzer": "medicine_analyzer"
                },

                "tests_advised": { "type": "keyword" },
                "follow_up": { "type": "text" },

                # Double-Nested Architecture
                "structured_data": {
                    "type": "nested",
                    "properties": {
                        "medicines": {
                            "type": "nested",
                            "properties": {
                                "name": {
                                    "type": "text",
                                    "analyzer": "medicine_analyzer",
                                    "fields": { "keyword": { "type": "keyword" } }
                                },
                                "dosage": { "type": "keyword" },
                                "frequency": { "type": "keyword" },
                                "duration": { "type": "keyword" },
                                "instructions": { "type": "text" }
                            }
                        }
                    }
                },

                "embedding_vector": {
                    "type": "dense_vector",
                    "dims": 768,
                    "index": True,
                    "similarity": "cosine"
                },

                "created_at": { "type": "date" }
            }
        }
    }

    print(f"--- Creating Enterprise Index: {new_index} ---")
    resp = requests.put(f"{base_url}/{new_index}", auth=auth, headers=headers, json=payload)
    print(f"Status: {resp.status_code}, Response: {resp.text}")

    if resp.status_code != 200:
        print("Failed to create index. Exiting.")
        return

    # 3. Double-Step Reindex (Zero Downtime Reindex)
    source_index = "prescriptions-prod-000004" # Latest generation from V4
    print(f"\n--- Reindexing from {source_index} to {new_index} ---")
    reindex_payload = {
        "source": { "index": source_index },
        "dest": { "index": new_index }
    }
    resp = requests.post(f"{base_url}/_reindex?wait_for_completion=true", auth=auth, headers=headers, json=reindex_payload)
    print(f"Status: {resp.status_code}, Response: {resp.text}")

    # 4. Final Atomic Alias Swap
    print("\n--- Final Atomic Alias Swap to Enterprise V5 ---")
    alias_payload = {
        "actions": [
            { "add": { "index": new_index, "alias": alias_name, "is_write_index": True }}
        ]
    }
    # Check if alias exists to swap safely
    alias_check = requests.get(f"{base_url}/_alias/{alias_name}", auth=auth)
    if alias_check.status_code == 200:
        existing_indices = list(alias_check.json().keys())
        for old_idx in existing_indices:
            alias_payload["actions"].insert(0, { "remove": { "index": old_idx, "alias": alias_name }})

    resp = requests.post(f"{base_url}/_aliases", auth=auth, headers=headers, json=alias_payload)
    print(f"Status: {resp.status_code}, Response: {resp.text}")

if __name__ == "__main__":
    upgrade_to_v5_final_production()
