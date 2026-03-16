# ES_API_KEY Authentication Setup Guide

## Summary of Changes Made

The codebase has been updated to support ES_API_KEY authentication for all FastAPI endpoints. The API key takes priority over basic authentication (username/password).

### Files Modified

1. **`.env`** - Added ES_API_KEY configuration
2. **`app/core/elasticsearch.py`** - Updated AsyncElasticsearch client to support API key auth
3. **`app/services/search/search_indexer.py`** - Updated sync client and health checks
4. **`scripts/utility/test_es_api_key_auth.py`** - Created test script (NEW)

## How ES_API_KEY Authentication Works

### For elasticsearch-py Client (Sync & Async)

The API key is split on the dot (`.`) into a tuple `(id, key)`:

```python
api_key_parts = settings.ES_API_KEY.split('.')
api_key_tuple = (api_key_parts[0], api_key_parts[1])
# Used as: api_key=api_key_tuple
```

### For Direct HTTP Health Checks

The API key is used directly in the Authorization header (it's already base64 encoded by Elasticsearch):

```python
headers["Authorization"] = f"ApiKey {settings.ES_API_KEY}"
```

## Testing the Authentication

Run the test script:

```bash
cd AI_OCR_Service
python scripts/utility/test_es_api_key_auth.py
```

## Creating the API Key on Elasticsearch

The 401 error indicates the API key needs to be created on the Elasticsearch server. Run this on your Elasticsearch instance:

### Method 1: Using curl (REST API)

```bash
# Create an API key
curl -X POST "http://localhost:9200/_security/api_key" \
  -H "Content-Type: application/json" \
  -u elastic:changeme123 \
  -d '{
    "name": "medvault-api-key",
    "expiration": "365d",
    "role_descriptors": {
      "medvault_role": {
        "cluster": ["monitor", "manage_index_templates"],
        "index": [
          {
            "names": ["prescriptions*", "prescriptions_current", "prescriptions-prod-write"],
            "privileges": ["create_index", "read", "write", "delete", "manage"]
          }
        ]
      }
    }
  }'
```

### Method 2: Using Kibana Dev Tools

```json
POST /_security/api_key
{
  "name": "medvault-api-key",
  "expiration": "365d",
  "role_descriptors": {
    "medvault_role": {
      "cluster": ["monitor", "manage_index_templates"],
      "index": [
        {
          "names": ["prescriptions*", "prescriptions_current", "prescriptions-prod-write"],
          "privileges": ["create_index", "read", "write", "delete", "manage"]
        }
      ]
    }
  }
}
```

The response will contain:

```json
{
  "id": "1fb34129a4d7416a9893ca419228edc4",
  "name": "medvault-api-key",
  "api_key": "D-O63fo1Ayv5WGnlvjf2D_jd",
  "encoded": "1fb34129a4d7416a9893ca419228edc4.D-O63fo1Ayv5WGnlvjf2D_jd",
  ...
}
```

Copy the `encoded` value to your `.env` file:

```env
ES_API_KEY="1fb34129a4d7416a9893ca419228edc4.D-O63fo1Ayv5WGnlvjf2D_jd"
```

## Fallback to Basic Auth

If you don't want to use API key authentication, simply comment out the ES_API_KEY in `.env`:

```env
# ES_API_KEY="..."
```

The system will automatically fall back to basic authentication using `ES_USER` and `ES_PASS`.

## Search & Chat Endpoints

All search endpoints now support ES_API_KEY:

- `/search/health` - Health check with API key auth
- `/search/medicine` - Medicine search
- `/search/provider` - Doctor/hospital search
- `/search/all` - Universal search
- `/search/semantic` - Semantic search
- `/search/hybrid` - Hybrid search
- `/search/comprehensive` - Intent-based smart search
- `/chat/medicine-chat` - Chat with medicine queries

All endpoints will use the configured ES_API_KEY automatically.

## Troubleshooting

### 401 Authentication Failed

- Verify the API key was created on the Elasticsearch server
- Check that the API key hasn't expired
- Ensure the API key has proper permissions for the indices

### Connection Refused

- Verify Elasticsearch is running at the configured ES_HOST
- Check firewall settings
- Ensure the ES_HOST URL is correct

### Index Not Found

- Run the setup script to create indices: `python scripts/setup/setup_elasticsearch.py`
- Or create indices manually as the elastic superuser
