"""
Test script to check Elasticsearch connection and status.
"""
import asyncio
import sys
from pathlib import Path

# Add AI_OCR_Service to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "AI_OCR_Service"))

from app.services.search.search_indexer import ElasticsearchClientFactory, AsyncSearchService

async def test_check_es():
    """Check Elasticsearch connection and index status."""
    print("=" * 60)
    print("Elasticsearch Connection Check")
    print("=" * 60)
    
    # Check if ES is enabled
    from app.core.config.config import settings
    print(f"\n1. Configuration:")
    print(f"   ELASTICSEARCH_ENABLED: {settings.ELASTICSEARCH_ENABLED}")
    print(f"   ELASTICSEARCH_HOST: {settings.ELASTICSEARCH_HOST}")
    print(f"   ES_INDEX: {settings.ES_INDEX}")
    
    if not settings.ELASTICSEARCH_ENABLED:
        print("\n   ERROR: Elasticsearch is disabled in configuration!")
        print("   Set ELASTICSEARCH_ENABLED=true in .env file")
        return False
    
    # Get client
    client = ElasticsearchClientFactory.get_async_client()
    if client is None:
        print("\n   ERROR: Failed to create Elasticsearch client")
        return False
    
    print(f"\n2. Client created successfully")
    
    try:
        # Test ping
        print(f"\n3. Testing connection (ping)...")
        ping = await client.ping()
        print(f"   Ping result: {ping}")
        
        if not ping:
            print("   ERROR: Elasticsearch ping failed - server not responding")
            return False
        
        # Get cluster info
        print(f"\n4. Getting cluster info...")
        info = await client.info()
        print(f"   Cluster name: {info.get('cluster_name', 'N/A')}")
        print(f"   Version: {info.get('version', {}).get('number', 'N/A')}")
        
        # Check index exists
        index_name = settings.ES_INDEX
        print(f"\n5. Checking index '{index_name}'...")
        exists = await client.indices.exists(index=index_name)
        print(f"   Index exists: {exists}")
        
        if not exists:
            print(f"\n   WARNING: Index '{index_name}' does not exist!")
            print("   You need to create it or run the indexing script.")
        
        await client.close()
        print(f"\n" + "=" * 60)
        print("Connection check completed successfully!")
        print("=" * 60)
        return True
        
    except Exception as e:
        print(f"\n   ERROR: {type(e).__name__}: {e}")
        print(f"\n   Troubleshooting:")
        print(f"   - Ensure Elasticsearch is running at {settings.ELASTICSEARCH_HOST}")
        print(f"   - Check if the ES server is accessible")
        print(f"   - Verify credentials if authentication is enabled")
        try:
            await client.close()
        except:
            pass
        return False

if __name__ == "__main__":
    success = asyncio.run(test_check_es())
    sys.exit(0 if success else 1)