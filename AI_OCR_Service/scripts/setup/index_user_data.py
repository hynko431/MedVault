"""
Script to index user-provided prescription data into Elasticsearch.
"""

from elasticsearch import Elasticsearch
import json
import time
import sys
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

# Elasticsearch connection settings
ES_HOST = "http://localhost:9200"
ES_USER = "elastic"
ES_PASS = "changeme123"
INDEX_NAME = "prescriptions_current"

user_data = [
    # 1. Gemini 2- flash lite
    {
      "prescription_id": "string",
      "structured_data": {
        "doctor_name": "Dr. Y. Lavanya",
        "hospital": "SAI CLINIC",
        "date": "2022-10-17",
        "patient_name": "Tet",
        "diagnosis": "Hypertension & Hypothyroid; Frever sine 3 days",
        "medicines": [
          {"name": "Tab Stamto smy", "dosage": None, "frequency": None, "duration": "30 day", "instructions": None},
          {"name": "Tab. Arvant snip", "dosage": None, "frequency": None, "duration": "30 day", "instructions": None},
          {"name": "Tab. Thyrox", "dosage": "75mcg", "frequency": None, "duration": "30 days", "instructions": None},
          {"name": "Tat Aplex fort", "dosage": None, "frequency": None, "duration": "30 days", "instructions": None}
        ]
      }
    },
    # 2. Gemini 2 flash with groq
    {
      "prescription_id": "string",
      "structured_data": {
        "doctor_name": "Dr. Y. Lavanya; Dr. K. Chanakya Chandra Kumar",
        "hospital": "SAI CLINIC",
        "date": "2022-10-17",
        "patient_name": "Tet",
        "diagnosis": "Hypertension & Hypothyroid",
        "medicines": [
          {"name": "Diab Shamto smy", "dosage": None, "frequency": None, "duration": "30 day", "instructions": None},
          {"name": "Tab. Aouwant soup", "dosage": None, "frequency": None, "duration": "30 day", "instructions": None},
          {"name": "Tab. Thuprax 75mcg", "dosage": None, "frequency": None, "duration": "30 days", "instructions": None},
          {"name": "fat Aplex part", "dosage": None, "frequency": None, "duration": "30 days", "instructions": None}
        ]
      }
    },
    # 3. Google vision ocr with groq
    {
      "prescription_id": "string",
      "structured_data": {
        "doctor_name": "Dr. Y. Lavanya",
        "hospital": "SAI CLINIC",
        "date": "2022-10-17",
        "patient_name": "Tet",
        "diagnosis": "Hypertension & Hypothyroid",
        "medicines": [
          {"name": "Tab. Ammont soup", "dosage": None, "frequency": None, "duration": "20 day", "instructions": None},
          {"name": "Arvant", "dosage": None, "frequency": None, "duration": None, "instructions": None},
          {"name": "Tob. Thyrax 75mg", "dosage": "75mg", "frequency": None, "duration": "30 days", "instructions": None},
          {"name": "Tat Aplex fast", "dosage": None, "frequency": None, "duration": "30 days", "instructions": None}
        ]
      }
    },
    # 4. gemini-2.5-flash-lite with groq
    {
      "prescription_id": "string",
      "structured_data": {
        "doctor_name": "Dr. K. Chanakya Chandra Kumar",
        "hospital": "SAI CLINIC",
        "date": "2022-10-17",
        "patient_name": None,
        "diagnosis": "c/o-Hypertension & Hypothyrod; c/o-Fever sins 3 days",
        "medicines": [
          {"name": "Tab Stanlo smg", "dosage": None, "frequency": None, "duration": "30 days", "instructions": None},
          {"name": "Tab. Arvant snp", "dosage": None, "frequency": None, "duration": "30 day", "instructions": None},
          {"name": "Tab. Thyraax 75mig", "dosage": None, "frequency": None, "duration": "30 days", "instructions": None},
          {"name": "Tab. Bplen fart", "dosage": None, "frequency": None, "duration": "30 days", "instructions": None}
        ]
      }
    },
    # 5. gemini-2.5-flash with groq
    {
      "prescription_id": "user123",
      "structured_data": {
        "doctor_name": "Dr. K. Chanakya Chandra Kumar",
        "hospital": "SAI CLINIC",
        "date": "2022-10-17",
        "patient_name": "Tet",
        "diagnosis": None,
        "medicines": [
          {"name": "Stamlo", "dosage": "5mg", "frequency": "0-1-0", "duration": "30 days", "instructions": None},
          {"name": "Arwant", "dosage": "5mg", "frequency": "0-1-0", "duration": "30 days", "instructions": None},
          {"name": "Thyrox", "dosage": "75mcg", "frequency": "1-0-0", "duration": "30 days", "instructions": None},
          {"name": "Bplex fort", "dosage": None, "frequency": "1-0-1", "duration": "30 days", "instructions": None}
        ]
      }
    },
    # 6. gemini-2.5-flash-preview-09-2025 with groq
    {
      "prescription_id": "user123",
      "structured_data": {
        "doctor_name": "Dr. Y. Lavanya; Dr. K. Chanakya Chandra Kumar",
        "hospital": "SAI CLINIC",
        "date": "2022-10-17",
        "patient_name": "Tet",
        "diagnosis": "Hypertension & Hypothyroid",
        "medicines": [
          {"name": "Tab. Stamlo", "dosage": "5 mg", "frequency": None, "duration": "30 days", "instructions": None},
          {"name": "Tab. Arvant", "dosage": "5 mg", "frequency": None, "duration": "30 days", "instructions": None},
          {"name": "Tab. Thyrox", "dosage": "75 mcg", "frequency": None, "duration": "30 days", "instructions": None},
          {"name": "Tab. Bplex fort", "dosage": None, "frequency": None, "duration": "30 days", "instructions": None}
        ]
      }
    },
    # 7. gemini 2.5 flash with openrouter
    {
      "prescription_id": "Test123",
      "structured_data": {
        "doctor_name": "Dr. Y. Lavanya",
        "hospital": "SAI CLINIC",
        "date": "2022-10-17",
        "patient_name": "Tet",
        "diagnosis": "Hypertension & Hypothyroid, Fever since 3 days",
        "medicines": [
          {"name": "Stamlo", "dosage": "5mg", "frequency": None, "duration": "30day", "instructions": None},
          {"name": "Arvant", "dosage": "5mg", "frequency": None, "duration": "30 day", "instructions": None},
          {"name": "Thyrox", "dosage": "75mg", "frequency": None, "duration": "30 days", "instructions": None},
          {"name": "Bplex fort", "dosage": None, "frequency": None, "duration": "30 days", "instructions": None}
        ]
      }
    },
    # 8. gemini-3-flash-preview with groq (different structure)
    {
      "patient_name": "Rina Paul.",
      "doctor_name": ["Dr Moumita Debnath"],
      "date": "2024-07-02",
      "diagnosis": ["Burning micturition"],
      "medicines": [
        {"name": "Numlo-TM", "dosage": "(5)", "frequency": "1 - 0 - x - x -", "duration": "Cont.", "form": "tab", "route": "ODPC"},
        {"name": "Vylda-DM", "dosage": "(100/10/1000)", "frequency": "- x - 0 - x -", "duration": "Cont", "instructions": "দুপুরে খাওয়ার আগে", "form": "tab", "route": "ODAC"},
        {"name": "Zerodol-P", "form": "tab", "route": "BDPC"},
        {"name": "Melmel SR", "dosage": "(500)", "frequency": "x 5 days - x - x - 0 -", "duration": "Cont.", "instructions": "রাতে খাওয়ার আগে", "form": "tab", "route": "ODAC"},
        {"name": "Candid-V", "frequency": "locally", "instructions": "apply", "form": "ointment"},
        {"name": "Ecaspirin-AV", "dosage": "(75/10)", "frequency": "- x - x - 0 -", "duration": "Cont.", "instructions": "রাতে খাওয়ার পর", "form": "tab", "route": "ODHS"},
        {"name": "Alkazol", "dosage": "2 tsf c", "instructions": "one glassof water", "form": "syrup"},
        {"name": "Rabiros-D", "duration": "1 month", "form": "capsule", "route": "ODAC"},
        {"name": "Vibrante", "frequency": "TDS", "duration": "7 days", "form": "tab", "route": "ODPC"},
        {"name": "Lfx", "dosage": "(750)", "duration": "7 days", "form": "tab", "route": "ODPC"}
      ]
    },
    # 9. Gemini 3.0 flash with openrouter (different structure)
    {
      "patient_name": "Rina Paul",
      "doctor_name": ["Dr Moumita Debnath"],
      "date": "2024-07-02",
      "diagnosis": ["Burning micturition", "FBS: 203", "PPBS: 298"],
      "medicines": [
        {"name": "T. Numlo-TM (5)", "dosage": "1 tab", "frequency": "O - X - X -", "duration": "Cont.", "instructions": "ODPC", "form": "tablet"},
        {"name": "T. Vylda-DM (100/10/1000)", "dosage": "1 tab", "frequency": "- X - O - X -", "duration": "Cont.", "instructions": "ODAC", "form": "tablet", "timing": "দুপুরে খাওয়ার আগে."},
        {"name": "T. Zerodol-P", "dosage": "1 tab", "frequency": "BDPC", "duration": "x 5 days", "form": "tablet"},
        {"name": "T. Melmet SR (500)", "dosage": "1 tab", "frequency": "X - X - O -", "duration": "Cont.", "instructions": "ODAC", "form": "tablet"},
        {"name": "Candid-V oint", "instructions": "apply locally রাতে খাওয়ার আগে.", "form": "ointment", "timing": "রাতে খাওয়ার আগে."},
        {"name": "Syr. Alkasol", "dosage": "2 tsf", "frequency": "TDS x 7 days", "instructions": "with one glassof water রাতে খাওয়ার পরে.", "form": "syrup", "timing": "রাতে খাওয়ার পরে."},
        {"name": "T. Ecaspirin-AV (75/10)", "dosage": "1 tab", "frequency": "X - X - O -", "duration": "Cont.", "instructions": "ODHS", "form": "tablet"},
        {"name": "T. Lfx (750)", "dosage": "1 tab", "frequency": "ODPC", "duration": "x 7 days", "form": "tablet"},
        {"name": "Cap. Rabiros-D", "dosage": "1 cap", "frequency": "ODAC", "duration": "1 month", "form": "capsule"},
        {"name": "T. Vibraute", "dosage": "1 tab", "frequency": "ODPC", "duration": "1 month", "form": "tablet"}
      ]
    }
]

def map_to_es(item, idx):
    """Map user provided structure to ES schema."""
    if "structured_data" in item:
        sd = item["structured_data"]
        medicines = sd.get("medicines", [])
        medicine_names = [m.get("name") for m in medicines if m.get("name")]
        
        # Parse date
        date_str = sd.get("date")
        try:
            created_at = datetime.strptime(date_str, "%Y-%m-%d").isoformat() + "Z"
        except:
            created_at = datetime.now().isoformat() + "Z"

        return {
            "prescription_id": f"user_rx_{idx:03d}",
            "user_id": str(idx),
            "doctor_name": sd.get("doctor_name"),
            "hospital": sd.get("hospital"),
            "patient_name": sd.get("patient_name"),
            "medicine_names": medicine_names,
            "diagnosis": sd.get("diagnosis"),
            "raw_text": f"Doctor: {sd.get('doctor_name')}. Medicines: {', '.join(medicine_names)}. Diagnosis: {sd.get('diagnosis')}",
            "created_at": created_at,
            "medicines": medicines,
            "doctor": {"name": sd.get("doctor_name")},
            "hospital_info": {"name": sd.get("hospital")},
            "embedding_vector": [0.1] * 768  # Placeholder for hybrid search
        }
    else:
        # Gemini 3.0 structure
        medicines = item.get("medicines", [])
        medicine_names = [m.get("name") for m in medicines if m.get("name")]
        
        # Parse date
        date_str = item.get("date")
        try:
            created_at = datetime.strptime(date_str, "%Y-%m-%d").isoformat() + "Z"
        except:
            created_at = datetime.now().isoformat() + "Z"

        # Handle list vs string for doctor_name
        doc_name = item.get("doctor_name")
        if isinstance(doc_name, list):
            doc_name = ", ".join(doc_name)
            
        diagnosis = item.get("diagnosis")
        if isinstance(diagnosis, list):
            diagnosis = "; ".join(diagnosis)

        return {
            "prescription_id": f"user_rx_{idx:03d}",
            "user_id": str(idx),
            "doctor_name": doc_name,
            "hospital": item.get("hospital", "Unknown Hospital"),
            "patient_name": item.get("patient_name"),
            "medicine_names": medicine_names,
            "diagnosis": diagnosis,
            "raw_text": f"Doctor: {doc_name}. Medicines: {', '.join(medicine_names)}. Diagnosis: {diagnosis}",
            "created_at": created_at,
            "medicines": medicines,
            "doctor": {"name": doc_name},
            "patient": {"name": item.get("patient_name")},
            "embedding_vector": [0.1] * 768  # Placeholder for hybrid search
        }

def index_data(es_client):
    print(f"\nIndexing {len(user_data)} user-provided prescriptions...")
    for i, item in enumerate(user_data, 1):
        doc = map_to_es(item, i)
        try:
            es_client.index(
                index=INDEX_NAME,
                id=doc["prescription_id"],
                document=doc
            )
            print(f"  ✅ Indexed: {doc['prescription_id']} (Doctor: {doc['doctor_name']})")
        except Exception as e:
            print(f"  ❌ Error indexing {doc['prescription_id']}: {e}")

def main():
    print("="*60)
    print("INDEXING USER-PROVIDED DATA")
    print("="*60)
    
    es_client = Elasticsearch(
        hosts=[ES_HOST],
        basic_auth=(ES_USER, ES_PASS),
        verify_certs=False,
        request_timeout=30
    )
    
    if not es_client.ping():
        print("❌ Failed to connect to Elasticsearch!")
        return
    
    index_data(es_client)
    
    print("\nRefreshing index...")
    es_client.indices.refresh(index=INDEX_NAME)
    print("✅ Index refreshed!")
    
    # Verify count
    count = es_client.count(index=INDEX_NAME)
    print(f"\nTotal documents in index: {count['count']}")
    
    print("\n" + "="*60)
    print("INDEXING COMPLETE!")
    print("="*60)

if __name__ == "__main__":
    main()
