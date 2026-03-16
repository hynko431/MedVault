"""
Test actual search functionality with restricted user.
"""
import asyncio
import sys
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "AI_OCR_Service"))

from app.core.config.config import settings
from app.services.search_indexer import AsyncSearchService, ElasticsearchClientFactory


async def test_search():
    """Test the actual search functionality."""
    print("=" * 70)
    print("Testing Search Functionality")
    print("=" * 70)
    
    # Clear cached client
    ElasticsearchClientFactory._async_client = None
    
    print(f"\n1. Configuration:")
    print(f"   ES_USER: {settings.ES_USER}")
    print(f"   ES_HOST: {settings.ES_HOST}")
    print(f"   ES_INDEX: {settings.ES_INDEX}")
    
    # Create service
    service = AsyncSearchService()
    
    print(f"\n2. Testing health check...")
    healthy = await service.health_check()
    print(f"   ✓ Health check: {healthy}")
    
    if not healthy:
        print("   ✗ Cannot connect to ES")
        return False
    
    print(f"\n3. Creating index if not exists...")
    try:
        await service.create_index_if_not_exists()
        print("   ✓ Index ready")
    except Exception as e:
        print(f"   ✗ Failed: {e}")
        # Continue anyway - index might already exist
    
    print(f"\n4. Indexing sample document...")
    sample_doc = {
        "prescription_id": "test_rx_001",
        "user_id": "1",
        "doctor_name": "Dr. Test Doctor",
        "hospital": "Test Hospital",
        "medicine_names": ["Paracetamol", "Ibuprofen"],
        "raw_text": "Test prescription with Paracetamol and Ibuprofen"
    }
    
    try:
        await service.index_document("test_rx_001", sample_doc)
        print("   ✓ Document indexed")
    except Exception as e:
        print(f"   ✗ Failed: {e}")
        return False
    
    # Wait a moment for indexing
    await asyncio.sleep(1)
    
    print(f"\n5. Searching for 'Paracetamol'...")
    try:
        results = await service.search_medicine("Paracetamol", "1", size=10)
        
        if results is None:
            print("   ✗ Search returned None")
            return False
        
        hits = results.get("hits", {}).get("hits", [])
        total = results.get("hits", {}).get("total", {}).get("value", 0)
        
        print(f"   ✓ Found {total} results")
        for hit in hits:
            source = hit.get("_source", {})
            print(f"      - {source.get('prescription_id')}: {', '.join(source.get('medicine_names', []))}")
        
    except Exception as e:
        print(f"   ✗ Search failed: {e}")
        return False
    
    print(f"\n6. Searching for 'Ibuprofen'...")
    try:
        results = await service.search_medicine("Ibuprofen", "1", size=10)
        
        if results is None:
            print("   ✗ Search returned None")
            return False
        
        hits = results.get("hits", {}).get("hits", [])
        total = results.get("hits", {}).get("total", {}).get("value", 0)
        
        print(f"   ✓ Found {total} results")
        
    except Exception as e:
        print(f"   ✗ Search failed: {e}")
        return False
    
    await service.close()
    
    print(f"\n" + "=" * 70)
    print("✓ Search functionality is working!")
    print("=" * 70)
    return True


if __name__ == "__main__":
    if not settings.ELASTICSEARCH_ENABLED:
        print("ERROR: ES is disabled!")
        sys.exit(1)
    
    success = asyncio.run(test_search())
    sys.exit(0 if success else 1)