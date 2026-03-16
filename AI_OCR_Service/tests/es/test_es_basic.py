"""Basic ES connection test."""
import asyncio
import sys
import os

# Change to AI_OCR_Service directory for .env loading
os.chdir(os.path.join(os.path.dirname(__file__), '..', 'AI_OCR_Service'))
sys.path.insert(0, os.getcwd())

from app.core.config.config import settings
from app.services.search_indexer import ElasticsearchClientFactory


async def test_connection():
    """Test Elasticsearch connection."""
    print("=" * 60)
    print("Elasticsearch Connection Test")
    print("=" * 60)
    
    print(f"\n1. Configuration:")
    print(f"   ELASTICSEARCH_ENABLED: {settings.ELASTICSEARCH_ENABLED}")
    print(f"   ES_HOST: {settings.ES_HOST}")
    print(f"   ES_USER: {settings.ES_USER}")
    print(f"   ES_INDEX: {settings.ES_INDEX}")
    print(f"   ES_VERIFY_CERTS: {settings.ES_VERIFY_CERTS}")
    print(f"   ES_TIMEOUT: {settings.ES_TIMEOUT}")
    print(f"   ES_MAX_RETRIES: {settings.ES_MAX_RETRIES}")
    
    if not settings.ELASTICSEARCH_ENABLED:
        print("\n   ERROR: Elasticsearch is disabled in configuration!")
        return False
    
    print(f"\n2. Creating client...")
    client = ElasticsearchClientFactory.get_async_client()
    
    if client is None:
        print("   ERROR: Failed to create Elasticsearch client")
        return False
    
    print(f"   Client created successfully")
    
    try:
        print(f"\n3. Testing connection (ping)...")
        ping = await client.ping()
        print(f"   Ping result: {ping}")
        
        if not ping:
            print("   ERROR: Elasticsearch ping failed - server not responding")
            return False
        
        print(f"\n4. Getting cluster info...")
        info = await client.info()
        print(f"   Cluster name: {info.get('cluster_name', 'N/A')}")
        print(f"   Version: {info.get('version', {}).get('number', 'N/A')}")
        
        print(f"\n" + "=" * 60)
        print("✅ Connection successful!")
        print("=" * 60)
        return True
        
    except Exception as e:
        print(f"\n   ERROR: {type(e).__name__}: {e}")
        print(f"\n   Troubleshooting:")
        print(f"   - Ensure Elasticsearch is running at {settings.ES_HOST}")
        print(f"   - Check if the ES server is accessible")
        print(f"   - Verify credentials (user: {settings.ES_USER})")
        return False
    finally:
        await client.close()


if __name__ == "__main__":
    success = asyncio.run(test_connection())
    sys.exit(0 if success else 1)