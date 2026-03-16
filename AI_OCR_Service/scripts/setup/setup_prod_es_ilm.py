import os
import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from app.core.config.config import settings

async def setup_ilm_and_template():
    if not settings.ELASTICSEARCH_ENABLED:
        print("Elasticsearch is disabled in config.")
        return

    from elasticsearch import AsyncElasticsearch
    client = AsyncElasticsearch(
        hosts=[settings.ELASTICSEARCH_HOST],
        basic_auth=(settings.ES_USER, settings.ES_PASS),
        verify_certs=settings.ES_VERIFY_CERTS
    )
    
    if not client:
        print("Failed to initialize ES client.")
        return

    try:
        # Step 2: Create ILM Policy
        print("Creating ILM Policy 'prescriptions-ilm'...")
        await client.ilm.put_lifecycle(
            name="prescriptions-ilm",
            policy={
                "phases": {
                    "hot": {
                        "actions": {
                            "rollover": {
                                "max_primary_shard_size": "5gb",
                                "max_age": "30d"
                            }
                        }
                    },
                    "delete": {
                        "min_age": "365d",
                        "actions": {
                            "delete": {}
                        }
                    }
                }
            }
        )
        print("ILM Policy created successfully.")

        # Step 3: Create Index Template
        print("Creating Index Template 'prescriptions-template'...")
        
        # Define settings with custom synonym analyzer
        index_settings = {
            "number_of_shards": 1,
            "number_of_replicas": settings.ES_REPLICAS,
            "index.lifecycle.name": "prescriptions-ilm",
            "index.lifecycle.rollover_alias": "prescriptions-prod-write",
            "analysis": {
                "filter": {
                    "synonym_filter": {
                        "type": "synonym_graph",
                        "synonyms": ["dummy=>dummy"],
                        "updateable": True
                    }
                },
                "analyzer": {
                    "synonym_analyzer": {
                        "tokenizer": "standard",
                        "filter": ["lowercase", "synonym_filter"]
                    }
                }
            }
        }
        
        mappings = {
            "properties": {
                "raw_text": { "type": "text" },
                "embedding_vector": {
                    "type": "dense_vector",
                    "dims": 768,
                    "index": True,
                    "similarity": "cosine"
                },
                "user_id": { "type": "keyword" },
                "created_at": { "type": "date" },
                "medicine_names": { 
                    "type": "text",
                    "fields": {
                        "synonym": {
                            "type": "text",
                            "analyzer": "standard",
                            "search_analyzer": "synonym_analyzer"
                        }
                    }
                },
                "doctor_name": { "type": "text" },
                "hospital": { "type": "text" },
                "diagnosis": { "type": "text" }
            }
        }
        
        await client.indices.put_index_template(
            name="prescriptions-template",
            index_patterns=["prescriptions-prod-*"],
            priority=100,
            template={
                "settings": index_settings,
                "mappings": mappings
            }
        )
        print("Index Template created successfully.")

        # Step 4: Create Initial Write Index
        index_name = "prescriptions-prod-000001"
        try:
            exists = await client.indices.exists(index=index_name)
            if not exists:
                print(f"Creating initial index '{index_name}'...")
                await client.indices.create(
                    index=index_name,
                    aliases={
                        "prescriptions-prod-write": { "is_write_index": True },
                        "prescriptions-prod-read": {}
                    }
                )
                print(f"Initial index '{index_name}' created successfully with aliases.")
            else:
                print(f"Index '{index_name}' already exists.")
        except Exception as create_err:
            print(f"Notice during index creation (might already exist): {create_err}")

        # Step 5: Update Cluster Settings
        print("Updating Cluster settings for allocation...")
        await client.cluster.put_settings(
            persistent={
                "cluster.routing.allocation.enable": "all"
            }
        )
        print("Cluster settings updated.")

    except Exception as e:
        print(f"Error during setup: {e}")
        # Safe way to access ES specific error info if available
        info = getattr(e, 'info', None)
        if info:
            print(f"Details: {info}")
    finally:
        await client.close()

if __name__ == "__main__":
    asyncio.run(setup_ilm_and_template())
