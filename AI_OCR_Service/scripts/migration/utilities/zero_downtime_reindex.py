import asyncio
import logging
import sys
import argparse
from pathlib import Path
from typing import Dict, Any, Optional

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from datetime import datetime
from app.services.search.search_indexer import ElasticsearchClientFactory
from app.core.config.config import settings

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def zero_downtime_reindex(source_version: int, target_version: int):
    """
    Formalized 5-step zero-downtime reindex procedure.
    """
    client = ElasticsearchClientFactory.get_async_client()
    if client is None:
        logger.error("Elasticsearch client is disabled or unavailable")
        return

    read_alias = "prescriptions-prod-read"
    write_alias = "prescriptions-prod-write"
    
    source_index = f"prescriptions-prod-{source_version:06d}"
    target_index = f"prescriptions-prod-{target_version:06d}"
    
    logger.info(f"🚀 Starting zero-downtime migration: {source_index} -> {target_index}")

    try:
        # Step 1: Ensure Template is updated (Assumed done via setup scripts or manual PUT)
        logger.info("Step 1: Verify template (Assumed updated)")

        # Step 2: Create New Index
        exists = await client.indices.exists(index=target_index)
        if not exists:
            logger.info(f"Step 2: Creating new index {target_index}")
            await client.indices.create(index=target_index)
        else:
            logger.warning(f"Step 2: Index {target_index} already exists. Skipping creation.")

        # Step 3: Reindex
        logger.info(f"Step 3: Reindexing from {source_index} to {target_index}...")
        reindex_response = await client.reindex(
            body={
                "source": {"index": source_index},
                "dest": {"index": target_index}
            },
            wait_for_completion=True
        )
        logger.info(f"Reindex complete: {reindex_response.get('total', 0)} documents processed.")

        # Step 4: Atomic Alias Swap
        logger.info("Step 4: Executing atomic alias swap...")
        actions = []
        
        # Handle Read Alias
        actions.append({"remove": {"index": source_index, "alias": read_alias}})
        actions.append({"add": {"index": target_index, "alias": read_alias}})
        
        # Handle Write Alias
        actions.append({"remove": {"index": source_index, "alias": write_alias}})
        # Ensure is_write_index is correctly handled for the API
        actions.append({
            "add": {
                "index": target_index, 
                "alias": write_alias, 
                "is_write_index": True # type: ignore[dict-item]
            }
        })
        
        await client.indices.update_aliases(body={"actions": actions})
        logger.info("✅ Alias swap successful. Production traffic is now hitting the new index.")

        # Step 5: Cleanup instructions
        logger.info(f"Step 5: Migration complete. Verify {target_index} before deleting {source_index}.")
        logger.info(f"To delete: DELETE {source_index}")

    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
    finally:
        await client.close()

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Zero-downtime ES migration script")
    parser.add_argument("--source", type=int, required=True, help="Current index version (e.g. 2)")
    parser.add_argument("--target", type=int, required=True, help="Target index version (e.g. 3)")
    
    args = parser.parse_args()
    asyncio.run(zero_downtime_reindex(args.source, args.target))
