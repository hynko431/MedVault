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
    ElasticsearchClientFactory
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def migrate_v1_to_v2():
    """Migrate existing prescriptions from v1 to v2 using native reindex API."""
    logger.info("Starting migration from semantic_v1 to semantic_v2...")
    
    if not settings.ELASTICSEARCH_ENABLED:
        logger.error("Elasticsearch is disabled in settings.")
        return

    # Using sync client because IndexMigrationManager uses sync client
    client = ElasticsearchClientFactory.get_sync_client()
    if not client:
        logger.error("Failed to initialize Elasticsearch sync client.")
        return

    migration_mgr = IndexMigrationManager(client)
    
    # 1. Create the new semantic index (v2)
    # The search_indexer mapping has been updated to use int8_hnsw
    new_index = migration_mgr.create_versioned_index("semantic_v2")
    if not new_index:
        logger.error("Failed to create new index prescriptions_semantic_v2. Checking if it exists...")
        new_index = "prescriptions_semantic_v2"
        # It may already exist, let's proceed to reindex
    
    logger.info(f"Using new semantic index: {new_index}")

    source_index = "prescriptions_semantic_v1"
    
    try:
        # Check source count
        resp = client.count(index=source_index)
        total_docs = resp.get("count", 0)
        logger.info(f"Found {total_docs} documents to migrate from {source_index}")
        
        if total_docs == 0:
            logger.info("No documents to migrate.")
            return

        # 2. Reindex Data
        logger.info(f"Reindexing data from {source_index} to {new_index}...")
        success = migration_mgr.reindex_data(source_index, new_index)

        if not success:
            logger.error("Reindexing failed. Aborting alias switch.")
            return

        # 3. Verify Reindex
        logger.info("Verifying reindexed data...")
        if not migration_mgr.verify_reindex(source_index, new_index):
            logger.error("Verification failed. Target index has fewer documents. Aborting alias switch.")
            return
            
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
    asyncio.run(migrate_v1_to_v2())
