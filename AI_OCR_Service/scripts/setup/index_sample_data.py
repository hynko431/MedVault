"""
Script to index sample prescription data into Elasticsearch.
Run this script to populate the index with test data.
"""

from elasticsearch import Elasticsearch
import json
import time
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

# Elasticsearch connection settings
ES_HOST = "http://localhost:9200"
ES_USER = "elastic"
ES_PASS = "changeme123"
INDEX_NAME = "prescriptions_current"

def create_index(es_client):
    """Create the index with proper mappings."""
    print(f"Creating index '{INDEX_NAME}' with mappings...")
    
    mapping = {
        "settings": {
            "number_of_shards": 1,
            "analysis": {
                "analyzer": {
                    "english_custom": {
                        "type": "standard",
                        "stopwords": "_english_"
                    },
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
                "patient_name": {"type": "text"},
                "diagnosis": {"type": "text"},
                "raw_text": {
                    "type": "text",
                    "analyzer": "english_custom"
                },
                "created_at": {"type": "date"},
                "medicines": {"type": "object"},
                "doctor": {"type": "object"},
                "hospital_info": {"type": "object"},
                "patient": {"type": "object"}
            }
        }
    }
    
    try:
        if es_client.indices.exists(index=INDEX_NAME):
            print(f"Index '{INDEX_NAME}' already exists. Deleting and recreating...")
            es_client.indices.delete(index=INDEX_NAME)
        
        es_client.indices.create(index=INDEX_NAME, body=mapping)
        print(f"✅ Index '{INDEX_NAME}' created successfully!")
    except Exception as e:
        print(f"❌ Error creating index: {e}")
        return False
    return True


def index_documents(es_client):
    """Index sample prescription documents."""
    
    documents = [
        {
            "_id": "rx_001",
            "doc": {
                "prescription_id": "rx_001",
                "user_id": "1",
                "doctor_name": "Dr. Sarah Johnson",
                "hospital": "City Medical Center",
                "patient_name": "John Doe",
                "medicine_names": ["Paracetamol", "Ibuprofen", "Vitamin D"],
                "diagnosis": ["Fever", "Body Pain"],
                "raw_text": "Paracetamol 500mg twice daily for fever, Ibuprofen 400mg as needed for body pain, Vitamin D 1000 IU daily for deficiency",
                "created_at": "2024-01-15T10:30:00Z",
                "medicines": [
                    {"name": "Paracetamol", "dosage": "500mg", "frequency": "twice daily"},
                    {"name": "Ibuprofen", "dosage": "400mg", "frequency": "as needed"},
                    {"name": "Vitamin D", "dosage": "1000 IU", "frequency": "daily"}
                ],
                "doctor": {
                    "name": "Dr. Sarah Johnson",
                    "specialization": "General Medicine"
                },
                "hospital_info": {
                    "name": "City Medical Center",
                    "location": "Downtown"
                }
            }
        },
        {
            "_id": "rx_002",
            "doc": {
                "prescription_id": "rx_002",
                "user_id": "1",
                "doctor_name": "Dr. Michael Chen",
                "hospital": "General Hospital",
                "patient_name": "John Doe",
                "medicine_names": ["Amoxicillin", "Paracetamol"],
                "diagnosis": ["Bacterial Infection"],
                "raw_text": "Amoxicillin 500mg three times daily for 7 days for bacterial infection, Paracetamol for fever management",
                "created_at": "2024-02-20T14:00:00Z",
                "medicines": [
                    {"name": "Amoxicillin", "dosage": "500mg", "frequency": "three times daily", "duration": "7 days"},
                    {"name": "Paracetamol", "dosage": "500mg", "frequency": "as needed"}
                ],
                "doctor": {
                    "name": "Dr. Michael Chen",
                    "specialization": "Infectious Disease"
                }
            }
        },
        {
            "_id": "rx_003",
            "doc": {
                "prescription_id": "rx_003",
                "user_id": "2",
                "doctor_name": "Dr. Emily Williams",
                "hospital": "St. Mary's Hospital",
                "patient_name": "Jane Smith",
                "medicine_names": ["Metformin", "Atorvastatin"],
                "diagnosis": ["Type 2 Diabetes", "High Cholesterol"],
                "raw_text": "Metformin 500mg twice daily for diabetes management, Atorvastatin 10mg once daily for cholesterol control",
                "created_at": "2024-03-10T09:15:00Z",
                "medicines": [
                    {"name": "Metformin", "dosage": "500mg", "frequency": "twice daily"},
                    {"name": "Atorvastatin", "dosage": "10mg", "frequency": "once daily"}
                ],
                "doctor": {
                    "name": "Dr. Emily Williams",
                    "specialization": "Endocrinology"
                }
            }
        },
        {
            "_id": "rx_004",
            "doc": {
                "prescription_id": "rx_004",
                "user_id": "1",
                "doctor_name": "Dr. Sarah Johnson",
                "hospital": "City Medical Center",
                "patient_name": "John Doe",
                "medicine_names": ["Aspirin", "Clopidogrel"],
                "diagnosis": ["Heart Disease"],
                "raw_text": "Aspirin 81mg daily for heart health, Clopidogrel 75mg daily as blood thinner",
                "created_at": "2024-04-05T11:00:00Z",
                "medicines": [
                    {"name": "Aspirin", "dosage": "81mg", "frequency": "daily"},
                    {"name": "Clopidogrel", "dosage": "75mg", "frequency": "daily"}
                ]
            }
        },
        {
            "_id": "rx_005",
            "doc": {
                "prescription_id": "rx_005",
                "user_id": "1",
                "doctor_name": "Dr. Robert Brown",
                "hospital": "Memorial Hospital",
                "patient_name": "John Doe",
                "medicine_names": ["Lisinopril", "Hydrochlorothiazide", "Paracetamol"],
                "diagnosis": ["Hypertension"],
                "raw_text": "Lisinopril 10mg daily for blood pressure, Hydrochlorothiazide 12.5mg daily as diuretic, Paracetamol as needed for pain",
                "created_at": "2024-05-12T16:30:00Z",
                "medicines": [
                    {"name": "Lisinopril", "dosage": "10mg", "frequency": "daily"},
                    {"name": "Hydrochlorothiazide", "dosage": "12.5mg", "frequency": "daily"},
                    {"name": "Paracetamol", "dosage": "500mg", "frequency": "as needed"}
                ]
            }
        }
    ]
    
    print(f"\nIndexing {len(documents)} sample prescriptions...")
    for doc in documents:
        try:
            es_client.index(
                index=INDEX_NAME,
                id=doc["_id"],
                document=doc["doc"]
            )
            print(f"  ✅ Indexed: {doc['_id']} (user_id: {doc['doc']['user_id']})")
        except Exception as e:
            print(f"  ❌ Error indexing {doc['_id']}: {e}")
    
    print("\nIndexing complete!")


def verify_data(es_client):
    """Verify the indexed data."""
    print("\n" + "="*50)
    print("VERIFYING INDEXED DATA")
    print("="*50)
    
    # Check document count
    count = es_client.count(index=INDEX_NAME)
    print(f"\nTotal documents in index: {count['count']}")
    
    # Search for user_id=1
    print("\n--- Searching for user_id=1 (should return 4 documents) ---")
    query = {
        "size": 10,
        "query": {
            "bool": {
                "filter": [
                    {"term": {"user_id": "1"}}
                ]
            }
        }
    }
    result = es_client.search(index=INDEX_NAME, body=query)
    print(f"Found {result['hits']['total']['value']} documents for user_id=1")
    for hit in result['hits']['hits']:
        print(f"  - {hit['_id']}: {hit['_source'].get('medicine_names', [])}")
    
    # Search for Paracetamol
    print("\n--- Searching for 'Paracetamol' (user_id=1) ---")
    query = {
        "size": 10,
        "query": {
            "bool": {
                "must": [
                    {"match": {"medicine_names": "Paracetamol"}}
                ],
                "filter": [
                    {"term": {"user_id": "1"}}
                ]
            }
        }
    }
    result = es_client.search(index=INDEX_NAME, body=query)
    print(f"Found {result['hits']['total']['value']} documents containing 'Paracetamol'")
    for hit in result['hits']['hits']:
        print(f"  - {hit['_id']}: {hit['_source'].get('medicine_names', [])}")


def main():
    print("="*50)
    print("ELASTICSEARCH SAMPLE DATA INDEXER")
    print("="*50)
    
    # Create Elasticsearch client
    print(f"\nConnecting to Elasticsearch at {ES_HOST}...")
    es_client = Elasticsearch(
        hosts=[ES_HOST],
        basic_auth=(ES_USER, ES_PASS),
        verify_certs=False,
        request_timeout=30
    )
    
    # Test connection
    if not es_client.ping():
        print("❌ Failed to connect to Elasticsearch!")
        return
    
    print("✅ Connected to Elasticsearch successfully!")
    
    # Create index
    if not create_index(es_client):
        return
    
    # Wait a moment for index to be ready
    time.sleep(1)
    
    # Index documents
    index_documents(es_client)
    
    # Refresh index to make documents searchable
    print("\nRefreshing index...")
    es_client.indices.refresh(index=INDEX_NAME)
    print("✅ Index refreshed!")
    
    # Verify data
    verify_data(es_client)
    
    print("\n" + "="*50)
    print("INDEXING COMPLETE!")
    print("="*50)
    print(f"\nYou can now search using:")
    print(f"  - Kibana Dev Tools: http://localhost:5601/app/dev_tools#/console")
    print(f"  - FastAPI endpoints (when server is running):")
    print(f"    GET /search/medicine?q=Paracetamol&user_id=1")
    print(f"    GET /search/all?q=Paracetamol&user_id=1")
    print(f"    GET /search/provider?q=Sarah&user_id=1")


if __name__ == "__main__":
    main()
