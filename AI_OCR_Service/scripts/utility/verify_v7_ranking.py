import requests
import json
import time
from datetime import datetime, timedelta

def verify_v7_ranking_logic():
    base_url = "http://localhost:9200"
    auth = ("elastic", "changeme123")
    headers = {"Content-Type": "application/json"}
    index = "prescriptions" # Enterprise Alias
    
    user_id = "V7_RANKING_USER"
    
    # 1. Index V7 Ranking Test Data
    print("--- Preparing V7 Ranking Test Data ---")
    
    docs = [
        # Exactly matching doc
        {
            "prescription_id": "V7-EXACT",
            "user_id": user_id,
            "doctor_name": "Dr. Exact",
            "medicine_names": ["Paracetamol"],
            "structured_data": {
                "medicines": [{"name": "Paracetamol", "dosage": "500mg"}]
            },
            "created_at": datetime.now().isoformat()
        },
        # Fuzzy matching doc (Typo in raw text)
        {
            "prescription_id": "V7-FUZZY",
            "user_id": user_id,
            "doctor_name": "Dr. Fuzzy",
            "raw_text": "Patient has fever, needs Paracetamxl.",
            "created_at": datetime.now().isoformat()
        },
        # Old doc (To test recency decay)
        {
            "prescription_id": "V7-OLD",
            "user_id": user_id,
            "doctor_name": "Dr. Old",
            "medicine_names": ["Paracetamol"],
            "structured_data": {
                "medicines": [{"name": "Paracetamol", "dosage": "500mg"}]
            },
            "created_at": (datetime.now() - timedelta(days=60)).isoformat()
        }
    ]
    
    for doc in docs:
        requests.post(f"{base_url}/{index}/_doc/{doc['prescription_id']}?refresh=true", 
                      auth=auth, headers=headers, json=doc)
    print(f"Indexed {len(docs)} documents.")

    # 2. Verify Ranking Priority: Exact > Fuzzy
    print("\n--- Verifying Ranking Priority (Exact > Fuzzy) ---")
    # We'll use the search service logic indirectly via raw ES query mimicking what we built
    from app.services.search.search_indexer import QueryBuilder
    
    query = QueryBuilder.build_hardened_production_query("Paracetamol", user_id)
    resp = requests.post(f"{base_url}/{index}/_search", auth=auth, headers=headers, json=query)
    results = resp.json().get("hits", {}).get("hits", [])
    
    if len(results) >= 2:
        top_id = results[0]["_id"]
        second_id = results[1]["_id"]
        print(f"Top result: {top_id}, Second result: {second_id}")
        if top_id == "V7-EXACT" and second_id == "V7-FUZZY":
            print("✅ Success: Exact match outranked fuzzy match.")
        else:
            # Check scores
            print(f"Scores: Top={results[0]['_score']}, Second={results[1]['_score']}")

    # 3. Verify Recency Decay: New > Old (both exact)
    print("\n--- Verifying Recency Decay (Recent > Old) ---")
    # V7-EXACT and V7-OLD both match "Paracetamol" exactly, but EXACT is newer.
    found_exact = False
    found_old = False
    exact_rank = -1
    old_rank = -1
    for i, hit in enumerate(results):
        if hit["_id"] == "V7-EXACT":
            exact_rank = i
            found_exact = True
        if hit["_id"] == "V7-OLD":
            old_rank = i
            found_old = True
            
    if found_exact and found_old:
        if exact_rank < old_rank:
            print(f"✅ Success: Recent document (rank {exact_rank}) outranked old document (rank {old_rank}).")
        else:
            print(f"❌ Error: Old document outranked recent one.")

    # 4. Cleanup
    for doc in docs:
        requests.delete(f"{base_url}/{index}/_doc/{doc['prescription_id']}", auth=auth)

if __name__ == "__main__":
    verify_v7_ranking_logic()
