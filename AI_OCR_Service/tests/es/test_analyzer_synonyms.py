import sys
import asyncio
from pathlib import Path
from app.services.search.search_indexer import ElasticsearchClientFactory

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

async def test_analyzer():
    client = ElasticsearchClientFactory.get_async_client()
    if client is None:
        raise RuntimeError("Elasticsearch client is None")
    resp = await client.indices.analyze(
        index="prescriptions_prod_v2",
        body={"analyzer": "medical_analyzer", "text": "heart attack"}
    )
    tokens = [t["token"] for t in resp["tokens"]]
    print("Tokens for 'heart attack':", tokens)
    
    resp2 = await client.indices.analyze(
        index="prescriptions_prod_v2",
        body={"analyzer": "medical_analyzer", "text": "painkiller"}
    )
    tokens2 = [t["token"] for t in resp2["tokens"]]
    print("Tokens for 'painkiller':", tokens2)

asyncio.run(test_analyzer())
