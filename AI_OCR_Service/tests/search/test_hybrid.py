import asyncio
import sys
import os

from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from app.services.search.search_indexer import AsyncSearchService, ElasticsearchClientFactory
from app.services.search.embeddings import embedding_service

async def test():
    client = ElasticsearchClientFactory.get_async_client()
    search_service = AsyncSearchService(client)
    
    # Use user_id='1' which matches the documents
    print("Generating query embedding...")
    query_vector = embedding_service.embed_query('blood pressure medicine')
    print("Executing hybrid search...")
    
    # Override index to use the hybrid index directly
    original_index = search_service._index_name
    search_service._index_name = "prescriptions_prod_v1"
    
    results = await search_service.hybrid_search(
        query='blood pressure medicine',
        user_id='1',  # Correct user_id
        query_vector=query_vector,
        size=5
    )
    
    search_service._index_name = original_index
    
    if results and results.get('hits'):
        hits = results['hits']['hits']
        print(f'Found {len(hits)} results:')
        for hit in hits:
            print(f"- Score: {hit['_score']:.4f}, ID: {hit['_source'].get('prescription_id')}, Medicines: {hit['_source'].get('medicine_names')}")
    else:
        print("No results found")

asyncio.run(test())
