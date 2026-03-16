import requests
import json
import time

def verify_v8_autocomplete():
    # Note: This assumes the FastAPI server is running. 
    # Since I cannot guarantee the server has rebooted with new code, 
    # I will also verify the ES query logic directly.
    
    base_url = "http://localhost:9200"
    auth = ("elastic", "changeme123")
    headers = {"Content-Type": "application/json"}
    index = "prescriptions"
    
    user_id = "V8_AUTO_USER"
    
    # 1. Index test data
    print("--- Preparing V8 Autocomplete Test Data ---")
    doc = {
        "prescription_id": "V8-AUTO-001",
        "user_id": user_id,
        "doctor_name": "Dr. Alessandro",
        "hospital": "Alpha Medical Center",
        "medicine_names": ["Amoxicillin"],
        "structured_data": {
            "medicines": [{"name": "Amoxicillin", "dosage": "500mg"}]
        }
    }
    requests.post(f"{base_url}/{index}/_doc/{doc['prescription_id']}?refresh=true", 
                  auth=auth, headers=headers, json=doc)

    # 2. Test Autocomplete Query Logic (Direct to ES)
    print("\n--- Verifying Autocomplete Logic (Direct to ES) ---")
    from app.services.search.search_indexer import QueryBuilder
    
    test_terms = ["ale", "amo"]
    
    for q in test_terms:
        body = QueryBuilder.build_autocomplete_search(q, user_id, 5)
        resp = requests.post(f"{base_url}/{index}/_search", auth=auth, headers=headers, json=body)
        search_data = resp.json()
        hits = search_data.get("hits", {}).get("hits", [])
        
        print(f"Query: '{q}' -> Hits: {len(hits)}")
        
        def extract_recursive(data):
            res = []
            if isinstance(data, list):
                for i in data: res.extend(extract_recursive(i))
            elif isinstance(data, dict):
                for v in data.values(): res.extend(extract_recursive(v))
            elif isinstance(data, (str, int, float)):
                res.append(str(data))
            return res

        found_suggestions = []
        for hit in hits:
            fields = hit.get("fields", {})
            found_suggestions.extend(extract_recursive(fields))
        
        # Filter out duplicates and print
        processed_suggestions = set(found_suggestions)
        
        print(f"Suggestions: {processed_suggestions}")
        if len(processed_suggestions) > 0:
            print(f"✅ Success: Autocomplete worked for '{q}'")
        else:
            print(f"❌ Error: No suggestions for '{q}'")

    # 3. Cleanup
    # requests.delete(f"{base_url}/{index}/_doc/V8-AUTO-001", auth=auth)

if __name__ == "__main__":
    verify_v8_autocomplete()
