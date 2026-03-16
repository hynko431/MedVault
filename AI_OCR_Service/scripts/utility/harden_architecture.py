import requests
import json
import sys

def harden_es_architecture():
    base_url = "http://localhost:9200"
    auth = ("elastic", "changeme123")
    headers = {"Content-Type": "application/json"}
    
    target_index = "prescriptions-prod-000004"
    alias_name = "prescriptions"
    
    # 1. Create/Standardize Alias
    print(f"--- Standardizing Alias: {alias_name} -> {target_index} ---")
    alias_payload = {
        "actions": [
            { "add": { "index": target_index, "alias": alias_name } }
        ]
    }
    resp = requests.post(f"{base_url}/_aliases", auth=auth, headers=headers, json=alias_payload)
    print(f"Alias Status: {resp.status_code}, Response: {resp.text}")
    
    # 2. Optimize Health (Set replicas to 0 for 1-node setup)
    print(f"\n--- Optimizing Cluster Health for {target_index} ---")
    settings_payload = {
        "index": { "number_of_replicas": 0 }
    }
    resp = requests.put(f"{base_url}/{target_index}/_settings", auth=auth, headers=headers, json=settings_payload)
    print(f"Settings Status: {resp.status_code}, Response: {resp.text}")
    
    # 3. Verify Health
    print("\n--- Final Cluster Health Check ---")
    resp = requests.get(f"{base_url}/_cluster/health", auth=auth)
    health = resp.json()
    print(json.dumps(health, indent=2))
    
    if health["status"] == "green":
        print("\n✅ Cluster is GREEN and architecture is hardened.")
    else:
        print(f"\n⚠️ Cluster status is {health['status']}. Checking unassigned shards...")
        resp = requests.get(f"{base_url}/_cat/shards?v&s=state", auth=auth)
        print(resp.text)

if __name__ == "__main__":
    harden_es_architecture()
