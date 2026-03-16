import asyncio
import logging
import sys
import os
from typing import List, Dict, Any

from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from app.core.config.config import settings
from app.services.search.search_indexer import (
    IndexMigrationManager, 
    AsyncSearchService,
    ElasticsearchClientFactory
)
from app.services.search.embeddings import embedding_service

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def migrate():
    """Migrate existing prescriptions to the new hybrid index with embeddings."""
    logger.info("Starting migration to Hybrid Search index...")
    
    if not settings.ELASTICSEARCH_ENABLED:
        logger.error("Elasticsearch is disabled in settings.")
        return

    client = ElasticsearchClientFactory.get_async_client()
    if not client:
        logger.error("Failed to initialize Elasticsearch client.")
        return

    migration_mgr = IndexMigrationManager(client)
    search_service = AsyncSearchService(client)
    
    # 1. Create the new production index
    # We use 'v1' as the version for this new production architecture
    new_index = migration_mgr.create_versioned_index("prod_v1")
    if not new_index:
        logger.error("Failed to create new index prescriptions_prod_v1 (it might already exist).")
        # Proceed anyway if it exists, or handle accordingly
        new_index = "prescriptions_prod_v1"
    
    logger.info(f"Using new index: {new_index}")

    # 2. Fetch all documents from the existing index
    # Note: We'll scan the alias 'prescriptions_all' to get current data
    source_index = "prescriptions_all"
    
    try:
        # Check source count
        resp = await client.count(index=source_index)
        total_docs = resp.get("count", 0)
        logger.info(f"Found {total_docs} documents to migrate from {source_index}")
        
        if total_docs == 0:
            logger.info("No documents to migrate.")
            return

        # 3. Batch processing loop
        batch_size = 50
        processed = 0
        
        # Use search_after for safe deep pagination during migration
        search_body = {
            "size": batch_size,
            "query": {"match_all": {}},
            "sort": [{"prescription_id": "asc"}]
        }
        
        while True:
            resp = await client.search(index=source_index, body=search_body)
            hits = resp["hits"]["hits"]
            if not hits:
                break
            
            # Prepare documents with embeddings
            bulk_data = []
            texts_to_embed = []
            docs_to_index = []
            
            for hit in hits:
                source = hit["_source"]
                # Build text to embed (same as used in QueryBuilder or as needed)
                # We'll use medicine names, diagnosis and raw text
                text = f"{source.get('medicine_names', '')} {source.get('diagnosis', '')} {source.get('raw_text', '')}"
                texts_to_embed.append(text)
                docs_to_index.append(source)
            
            # Generate embeddings (hybrid service handles API/Local fallback)
            embeddings = embedding_service.embed_documents(texts_to_embed)
            
            # Prepare bulk index actions
            for i, doc in enumerate(docs_to_index):
                doc["embedding_vector"] = embeddings[i]
                bulk_data.append({"index": {"_index": new_index, "_id": doc["prescription_id"]}})
                bulk_data.append(doc)
            
            # Perform bulk indexing
            if bulk_data:
                await client.bulk(operations=bulk_data, refresh=True)
            
            processed += len(hits)
            logger.info(f"Processed {processed}/{total_docs} documents...")
            
            # Get the sort value of the last hit for search_after
            search_body["search_after"] = hits[-1]["sort"]

    except Exception as e:
        logger.error(f"Migration failed during data processing: {e}")
        return

    # 4. Atomic Alias Switch
    logger.info(f"Switching alias {settings.ES_INDEX_ALIAS} to {new_index}...")
    success = migration_mgr.switch_alias_atomically(new_index)
    
    if success:
        logger.info("Migration COMPLETED SUCCESSFULLY.")
    else:
        logger.error("Alias switch failed. Please check Elasticsearch logs.")

if __name__ == "__main__":
    asyncio.run(migrate())
