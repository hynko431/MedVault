import requests
import json
import sys

def configure_slow_logs(index_name: str):
    url = f"http://localhost:9200/{index_name}/_settings"
    settings = {
        "index.search.slowlog.threshold.query.warn": "200ms",
        "index.search.slowlog.threshold.query.info": "100ms"
    }
    
    try:
        response = requests.put(
            url,
            auth=("elastic", "changeme123"),
            headers={"Content-Type": "application/json"},
            json=settings
        )
        if response.status_code == 200:
            print(f"✅ Slow logs enabled for {index_name}")
        else:
            print(f"❌ Failed to enable slow logs: {response.status_code}")
            print(response.text)
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    # Use the write alias to target the current active index
    configure_slow_logs("prescriptions-prod-write")
