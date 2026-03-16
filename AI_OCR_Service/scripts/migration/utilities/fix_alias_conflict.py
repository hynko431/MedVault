import os
import sys

from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from elasticsearch import Elasticsearch
from elasticsearch.exceptions import NotFoundError

def fix_indices():
    es = Elasticsearch(hosts=["http://localhost:9200"], basic_auth=("elastic", "changeme123"))
    
    # 1. Delete the conflicting index 'prescriptions'
    try:
        # We explicitly check if it's an index, not an alias to be safe
        index_status = es.indices.get(index="prescriptions")
        # If it returns info, and it's an index, delete it
        if "prescriptions" in index_status:
            print("Found conflicting index 'prescriptions'. Deleting...")
            es.indices.delete(index="prescriptions")
            print("Deleted.")
    except NotFoundError:
        print("Index 'prescriptions' does not exist. Safe to proceed.")
    except Exception as e:
        print(f"Info: {e}")

    # 2. Create alias correctly
    try:
        print("Adding alias 'prescriptions' to 'prescriptions_v1'...")
        es.indices.update_aliases(body={
            "actions": [
                {
                    "add": {
                        "index": "prescriptions_v1",
                        "alias": "prescriptions"
                    }
                }
            ]
        })
        print("Alias created successfully.")
    except Exception as e:
        print(f"Error creating alias: {e}")
        
    # 3. Set replicas to 0 for local dev
    try:
        print("Setting number_of_replicas to 0 on 'prescriptions_v1'...")
        es.indices.put_settings(index="prescriptions_v1", body={"number_of_replicas": 0})
        
        # Also check prescriptions-prod-000001 (which we created in the last step) 
        # to ensure the cluster is fully green if the user is running 1 node locally.
        print("Applying 0 replicas to 'prescriptions-prod-000001' as well for local green status...")
        es.indices.put_settings(index="prescriptions-prod-000001", body={"number_of_replicas": 0}, ignore_unavailable=True)
        
        print("Settings updated successfully.")
    except Exception as e:
        print(f"Error updating settings: {e}")

    # Output health status
    health = es.cluster.health()
    print(f"Cluster Status: {health.get('status')}")

if __name__ == "__main__":
    fix_indices()
