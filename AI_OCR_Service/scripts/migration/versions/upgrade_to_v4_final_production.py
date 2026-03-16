import requests
import json
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from app.core.config.config import settings

def upgrade_to_v4_final_production():
    base_url = settings.ES_HOST
    auth = (settings.ES_USER, settings.ES_PASS)
    headers = {"Content-Type": "application/json"}

    # 1. Define Final V4 Template
    template_name = "prescriptions-template"
    template_payload = {
        "index_patterns": ["prescriptions-prod-*"],
        "priority": 400,  # Highest priority
        "template": {
            "settings": {
                "number_of_shards": 1,
                "number_of_replicas": settings.ES_REPLICAS,
                "index.lifecycle.name": "prescriptions-ilm",
                "index.lifecycle.rollover_alias": "prescriptions-prod-write",
                "analysis": {
                    "filter": {
                        "edge_ngram_filter": {
                            "type": "edge_ngram",
                            "min_gram": 2,
                            "max_gram": 15
                        }
                    },
                    "analyzer": {
                        "ocr_index_analyzer": {
                            "type": "custom",
                            "tokenizer": "standard",
                            "filter": [
                                "lowercase",
                                "asciifolding",
                                "edge_ngram_filter"
                            ]
                        },
                        "ocr_search_analyzer": {
                            "type": "custom",
                            "tokenizer": "standard",
                            "filter": [
                                "lowercase",
                                "asciifolding"
                            ]
                        },
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
                    
                    # Autocomplete fields
                    "doctor_name": { "type": "search_as_you_type" },
                    "hospital": { "type": "search_as_you_type" },
                    "medicine_names": { "type": "search_as_you_type" },

                    "diagnosis": {
                        "type": "text",
                        "analyzer": "english_custom",
                        "fields": { "keyword": { "type": "keyword" } }
                    },
                    
                    # OCR-tolerant raw text
                    "raw_text": { 
                        "type": "text", 
                        "analyzer": "ocr_index_analyzer",
                        "search_analyzer": "ocr_search_analyzer"
                    },
                    
                    # Corrected Structured Data Nested Path
                    "structured_data": {
                        "properties": {
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
                            }
                        }
                    },
                    
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
                    },
                    "created_at": { "type": "date" },
                    "updated_at": { "type": "date" }
                }
            }
        }
    }

    print(f"--- Applying Final V4 template: {template_name} ---")
    resp = requests.put(f"{base_url}/_index_template/{template_name}", auth=auth, headers=headers, json=template_payload)
    print(f"Status: {resp.status_code}, Response: {resp.text}")

    # 2. Create Next Index Generation (v4)
    new_index = "prescriptions-prod-000004"
    print(f"\n--- Creating V4 index: {new_index} ---")
    resp = requests.put(f"{base_url}/{new_index}", auth=auth, headers=headers)
    print(f"Status: {resp.status_code}, Response: {resp.text}")

    # 3. Reindex
    source_index = "prescriptions-prod-000003"
    print(f"\n--- Reindexing from {source_index} to {new_index} ---")
    reindex_payload = {
        "source": { "index": source_index },
        "dest": { "index": new_index }
    }
    resp = requests.post(f"{base_url}/_reindex?wait_for_completion=true", auth=auth, headers=headers, json=reindex_payload)
    print(f"Status: {resp.status_code}, Response: {resp.text}")

    # 4. Atomic Alias Swap
    print("\n--- Final Atomic Alias Swap to V4 ---")
    alias_payload = {
        "actions": [
            { "remove": { "index": source_index, "alias": "prescriptions-prod-write" }},
            { "add": { "index": new_index, "alias": "prescriptions-prod-write", "is_write_index": True }},
            { "remove": { "index": source_index, "alias": "prescriptions-prod-read" }},
            { "add": { "index": new_index, "alias": "prescriptions-prod-read" }},
            { "remove": { "index": source_index, "alias": "prescriptions" }},
            { "add": { "index": new_index, "alias": "prescriptions" }}
        ]
    }
    resp = requests.post(f"{base_url}/_aliases", auth=auth, headers=headers, json=alias_payload)
    print(f"Status: {resp.status_code}, Response: {resp.text}")

if __name__ == "__main__":
    upgrade_to_v4_final_production()
