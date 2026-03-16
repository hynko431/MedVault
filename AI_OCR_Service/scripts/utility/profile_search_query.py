import requests
import json

def profile_query():
    url = "http://localhost:9200/prescriptions-prod-read/_search"
    query = {
        "profile": True,
        "query": {
            "bool": {
                "filter": [
                    { "term": { "user_id": "123" } }
                ],
                "must": [
                    {
                        "multi_match": {
                            "query": "parac 500",
                            "type": "bool_prefix",
                            "fields": [
                                "medicine_names",
                                "medicine_names._2gram",
                                "medicine_names._3gram"
                            ]
                        }
                    }
                ]
            }
        }
    }
    
    try:
        response = requests.post(
            url,
            auth=("elastic", "changeme123"),
            headers={"Content-Type": "application/json"},
            json=query
        )
        if response.status_code == 200:
            result = response.json()
            # Focus on the 'profile' section
            profile = result.get("profile", {})
            print("--- Search Profiling Result ---")
            for shard in profile.get("shards", []):
                print(f"Shard: {shard.get('id')}")
                for search in shard.get("searches", []):
                    for query_info in search.get("query", []):
                        print(f"  Type: {query_info.get('type')}")
                        print(f"  Time: {query_info.get('time_in_nanos') / 1_000_000:.2f}ms")
            
            print("\nProfile data saved to search_profile.json")
            with open("search_profile.json", "w") as f:
                json.dump(result, f, indent=2)
        else:
            print(f"❌ Profiling failed: {response.status_code}")
            print(response.text)
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    profile_query()
