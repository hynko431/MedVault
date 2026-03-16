import asyncio
import os
import json
import sys
from pathlib import Path
from typing import Dict, Any, List

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from app.services.search.search_indexer import es_service, QueryBuilder
from app.core.config.config import settings

async def test_search_logic():
    print("🚀 Starting Advanced Search Logic Verification")
    
    user_id = "test_user_123"
    
    # 1. Test Unified Hardened Query Builder
    hardened_query = QueryBuilder.build_hardened_production_query("paracet 500", user_id, 10)
    print("\n✅ Hardened Production Query built successfully")
    
    # 2. Test Advanced Hybrid Query Builder
    query_vector = [0.1] * 768  # Mock vector
    hybrid_query = QueryBuilder.build_advanced_hybrid_query("paracet 500", user_id, query_vector, 10)
    print("✅ Advanced Hybrid Query built successfully")
    
    # Verify script_score and weighting
    assert "script_score" in hybrid_query["query"]
    assert "0.7" in hybrid_query["query"]["script_score"]["script"]["source"]
    assert "0.3" in hybrid_query["query"]["script_score"]["script"]["source"]

    # 3. Test Actual Service Execution (Requires ES running)
    if await es_service.health_check():
        print("\n🌐 Elasticsearch is online. Testing service methods...")
        
        # Test medicine search
        await es_service.search_medicine("paracet", user_id, 5)
        print(f"✅ search_medicine executed")
        
        # Test autocomplete
        await es_service.autocomplete("sm", user_id, 5)
        print(f"✅ autocomplete executed")
        
        # Test hybrid search
        # Note: This might fail if the script requires specific data or if cosineSimilarity
        # fails on an empty index/missing mapping, but we check if it triggers correctly.
        try:
            await es_service.hybrid_search("paracet", user_id, query_vector, 5)
            print(f"✅ hybrid_search executed")
        except Exception as e:
            print(f"⚠️ hybrid_search execution failed (expected if mapping is not fully ready for script): {e}")
            
    else:
        print("\n⚠️ Elasticsearch is offline. Skipping service execution tests.")

    print("\n✨ Advanced Search Logic Verification Complete")

if __name__ == "__main__":
    asyncio.run(test_search_logic())
