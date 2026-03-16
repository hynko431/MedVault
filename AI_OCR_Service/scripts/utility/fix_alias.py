import requests
import json

def check_and_fix_alias():
    base_url = "http://localhost:9200"
    auth = ("elastic", "changeme123")
    headers = {"Content-Type": "application/json"}
    
    # Check what indices exist
    resp = requests.get(f"{base_url}/_cat/indices?v", auth=auth)
    print("Available indices:")
    print(resp.text)
    
    # Check if prescriptions_current is an index or alias
    resp_index = requests.get(f"{base_url}/prescriptions_current", auth=auth)
    if resp_index.status_code == 200:
        index_info = resp_index.json()
        if 'prescriptions_current' in index_info:
            print("\n✅ 'prescriptions_current' is an INDEX with data - no alias needed!")
            print(f"   Documents: Check the index list above")
            print("   Your .env already has: ES_INDEX=prescriptions_current")
            print("   The app should work correctly as-is.")
            return
    
    # Check current aliases
    resp_aliases = requests.get(f"{base_url}/_cat/aliases?v", auth=auth)
    print("\nCurrent aliases:")
    print(resp_aliases.text)
    
    # Check if prescriptions_current alias exists
    alias_check = requests.get(f"{base_url}/_alias/prescriptions_current", auth=auth)
    if alias_check.status_code == 200:
        print("\n✅ Alias 'prescriptions_current' already exists!")
        print(alias_check.text)
        return
    
    # If we get here, we need to create the alias
    # Find which index has data
    indices_resp = requests.get(f"{base_url}/_cat/indices?format=json", auth=auth)
    indices = indices_resp.json()
    
    target_index = None
    for idx in indices:
        if idx['index'].startswith('prescriptions') and idx['docs.count'] != '0':
            target_index = idx['index']
            print(f"\nFound index with data: {target_index} ({idx['docs.count']} docs)")
            break
    
    if not target_index:
        target_index = "prescriptions-prod-000002"
        print(f"\n⚠️ No index with data found. Using: {target_index}")
    
    # Create the alias
    payload = {
        "actions": [
            {
                "add": {
                    "index": target_index,
                    "alias": "prescriptions_current"
                }
            }
        ]
    }
    
    resp = requests.post(f"{base_url}/_aliases", auth=auth, headers=headers, json=payload)
    print(f"\nAlias creation response: {resp.status_code}")
    if resp.status_code == 200:
        print("✅ Alias created successfully!")
    else:
        print(f"Error: {resp.text}")
    
    # Verify the alias was created
    resp_verify = requests.get(f"{base_url}/_cat/aliases?v", auth=auth)
    print("\nUpdated aliases:")
    print(resp_verify.text)
    
if __name__ == "__main__":
    check_and_fix_alias()
