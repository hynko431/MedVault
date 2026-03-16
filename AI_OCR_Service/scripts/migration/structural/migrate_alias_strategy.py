import os
import asyncio
import sys

from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from app.core.config.config import settings
from app.services.search.search_indexer import ElasticsearchClientFactory

async def perform_migration():
    if not settings.ELASTICSEARCH_ENABLED:
        print("Elasticsearch is disabled.")
        return

    client = ElasticsearchClientFactory.get_async_client()
    if not client:
        print("Failed to init Client.")
        return
        
    old_index = settings.ES_INDEX # typically prescriptions_current or prescriptions_semantic_v1
    new_index = "prescriptions-prod-000001"
    
    try:
        # Check if old index exists
        if await client.indices.exists(index=old_index):
            print(f"Reindexing from {old_index} to {new_index}...")
            # Reindex
            await client.reindex(
                body={
                    "source": { "index": old_index },
                    "dest": { "index": new_index }
                },
                wait_for_completion=True
            )
            print("Reindexing complete.")
            
            # The new_index should already have the `prescriptions-prod-read` and `prescriptions-prod-write`
            # aliases configured from setup_prod_es_ilm.py script.
            print("Migration successful. The app can now switch to the alias.")
        else:
            print(f"Old index {old_index} not found. Skipping reindex.")
            
    except Exception as e:
        print(f"Migration error: {e}")
    finally:
        await client.close()

if __name__ == "__main__":
    asyncio.run(perform_migration())
