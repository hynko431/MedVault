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

# Use sentence-transformers directly for semantic search as per production architecture
try:
    from sentence_transformers import SentenceTransformer
except ImportError:
    print("Please install sentence-transformers: pip install sentence-transformers")
    sys.exit(1)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def build_semantic_text(doc: Dict[str, Any]) -> str:
    """Build the text payload for semantic embedding."""
    diagnosis = doc.get("diagnosis", "")
    if isinstance(diagnosis, list):
        diagnosis = ", ".join(diagnosis)
        
    medicine_names = doc.get("medicine_names", [])
    if isinstance(medicine_names, str):
        medicine_names = [medicine_names]
        
    symptoms = doc.get("symptoms", "")
    if isinstance(symptoms, list):
        symptoms = ", ".join(symptoms)
        
    raw_text = doc.get("raw_text", "")
    
    return f"""
Diagnosis: {diagnosis}
Symptoms: {symptoms}
Medicines: {", ".join(medicine_names)}
Clinical Notes: {raw_text}
""".strip()

async def migrate():
    """Migrate existing prescriptions to the new pure semantic index."""
    logger.info("Starting migration to Semantic Search index...")
    
    if not settings.ELASTICSEARCH_ENABLED:
        logger.error("Elasticsearch is disabled in settings.")
        return

    client = ElasticsearchClientFactory.get_async_client()
    if not client:
        logger.error("Failed to initialize Elasticsearch client.")
        return

    migration_mgr = IndexMigrationManager(client)
    
    # 1. Initialize Embedding Model
    logger.info("Loading SentenceTransformer model (Alibaba-NLP/gte-multilingual-base)...")
    model = SentenceTransformer("Alibaba-NLP/gte-multilingual-base", trust_remote_code=True)
    
    # 2. Create the new semantic index
    new_index = migration_mgr.create_versioned_index("semantic_v1")
    if not new_index:
        logger.error("Failed to create new index prescriptions_semantic_v1 (it might already exist).")
        new_index = "prescriptions_semantic_v1"
    
    logger.info(f"Using new semantic index: {new_index}")

    # 3. Fetch all documents from the existing index
    source_index = "prescriptions_all"
    
    try:
        # Check source count
        resp = await client.count(index=source_index)
        total_docs = resp.get("count", 0)
        logger.info(f"Found {total_docs} documents to migrate from {source_index}")
        
        if total_docs == 0:
            logger.info("No documents to migrate.")
            return

        # 4. Batch processing loop
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
                # Build semantic text
                semantic_text = build_semantic_text(source)
                texts_to_embed.append(semantic_text)
                docs_to_index.append(source)
            
            # Generate embeddings
            logger.info(f"Generating embeddings for {len(texts_to_embed)} documents...")
            embeddings = model.encode(texts_to_embed, normalize_embeddings=True)
            
            # Prepare bulk index actions
            for i, doc in enumerate(docs_to_index):
                doc["embedding_vector"] = embeddings[i].tolist()
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

    # 5. Atomic Alias Switch
    logger.info(f"Switching alias {settings.ES_INDEX_ALIAS} to {new_index}...")
    success = migration_mgr.switch_alias_atomically(new_index)
    
    if success:
        logger.info("Migration COMPLETED SUCCESSFULLY.")
    else:
        logger.error("Alias switch failed. Please check Elasticsearch logs.")

if __name__ == "__main__":
    asyncio.run(migrate())
