"""
Setup script for Elasticsearch - creates index and optionally adds sample data.
Run this after starting Elasticsearch with Docker.
"""
import asyncio
import sys
import argparse
from datetime import datetime, timezone
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from app.services.search.search_indexer import AsyncSearchService, ElasticsearchClientFactory
from app.core.config.config import settings


async def setup_elasticsearch(create_sample_data: bool = False):
    """Setup Elasticsearch index and optionally add sample data."""
    print("=" * 70)
    print("Elasticsearch Setup")
    print("=" * 70)
    
    print(f"\n1. Configuration:")
    print(f"   Host: {settings.ELASTICSEARCH_HOST}")
    print(f"   Index: {settings.ES_INDEX}")
    print(f"   Enabled: {settings.ELASTICSEARCH_ENABLED}")
    
    if not settings.ELASTICSEARCH_ENABLED:
        print("\n   ERROR: Elasticsearch is disabled in .env!")
        print("   Set ELASTICSEARCH_ENABLED=true and restart")
        return False
    
    # Get service
    service = AsyncSearchService()
    
    print(f"\n2. Testing connection...")
    try:
        healthy = await service.health_check()
        if not healthy:
            print("   ERROR: Cannot connect to Elasticsearch!")
            print(f"\n   To start Elasticsearch with Docker:")
            print("   docker run -d --name elasticsearch -p 9200:9200 \\")
            print("     -e discovery.type=single-node \\")
            print("     -e xpack.security.enabled=false \\")
            print("     elasticsearch:8.11.0")
            print(f"\n   Or download from: https://www.elastic.co/downloads/elasticsearch")
            return False
        print("   Connection successful!")
    except Exception as e:
        print(f"   ERROR: {e}")
        return False
    
    print(f"\n3. Creating index if not exists...")
    try:
        await service.create_index_if_not_exists()
        print(f"   Index '{settings.ES_INDEX}' is ready!")
    except Exception as e:
        print(f"   ERROR creating index: {e}")
        return False
    
    # Check if index is empty
    client = ElasticsearchClientFactory.get_async_client()
    try:
        if client is None:
            print(f"\n   ERROR: Client is None")
            await service.close()
            return False
            
        count_result = await client.count(index=settings.ES_INDEX)
        count = count_result.get("count", 0) if count_result else 0
        print(f"\n4. Current document count: {count}")
        
        if count == 0 and create_sample_data:
            print(f"\n5. Adding sample data...")
            await add_sample_data(service)
            print("   Sample data added successfully!")
        elif count == 0:
            print(f"\n   Index is empty. Use --sample-data flag to add sample prescriptions.")
    except Exception as e:
        print(f"\n   Could not check document count: {e}")
    
    await service.close()
    
    print(f"\n" + "=" * 70)
    print("Setup completed!")
    print("=" * 70)
    print(f"\nYou can now use the search API:")
    print(f"  GET /search/health          - Check search service health")
    print(f"  GET /search/medicine-async  - Search medicines")
    print(f"  GET /search/all             - Universal search")
    return True


async def add_sample_data(service: AsyncSearchService):
    """Add sample prescription data for testing."""
    sample_prescriptions = [
        {
            "prescription_id": "rx_001",
            "user_id": "1",
            "doctor_name": "Dr. Sarah Johnson",
            "hospital": "City Medical Center",
            "medicine_names": ["Paracetamol", "Ibuprofen", "Vitamin D"],
            "raw_text": "Paracetamol 500mg twice daily, Ibuprofen 400mg as needed, Vitamin D 1000 IU daily"
        },
        {
            "prescription_id": "rx_002",
            "user_id": "1",
            "doctor_name": "Dr. Michael Chen",
            "hospital": "General Hospital",
            "medicine_names": ["Amoxicillin", "Paracetamol"],
            "raw_text": "Amoxicillin 500mg three times daily for 7 days, Paracetamol for fever"
        },
        {
            "prescription_id": "rx_003",
            "user_id": "2",
            "doctor_name": "Dr. Emily Williams",
            "hospital": "St. Mary's Hospital",
            "medicine_names": ["Metformin", "Atorvastatin"],
            "raw_text": "Metformin 500mg twice daily, Atorvastatin 10mg once daily"
        },
        {
            "prescription_id": "rx_004",
            "user_id": "1",
            "doctor_name": "Dr. Sarah Johnson",
            "hospital": "City Medical Center",
            "medicine_names": ["Aspirin", "Clopidogrel"],
            "raw_text": "Aspirin 81mg daily, Clopidogrel 75mg daily"
        },
        {
            "prescription_id": "rx_005",
            "user_id": "1",
            "doctor_name": "Dr. Robert Brown",
            "hospital": "Memorial Hospital",
            "medicine_names": ["Lisinopril", "Hydrochlorothiazide", "Paracetamol"],
            "raw_text": "Lisinopril 10mg daily, Hydrochlorothiazide 12.5mg daily, Paracetamol as needed"
        }
    ]
    
    for doc in sample_prescriptions:
        try:
            # Add timestamp
            doc["created_at"] = datetime.now(timezone.utc).isoformat()
            await service.index_document(doc["prescription_id"], doc)
            print(f"   Added: {doc['prescription_id']} - {', '.join(doc['medicine_names'])}")
        except Exception as e:
            print(f"   ERROR adding {doc['prescription_id']}: {e}")


def main():
    parser = argparse.ArgumentParser(description="Setup Elasticsearch for MedVault")
    parser.add_argument(
        "--sample-data",
        action="store_true",
        help="Add sample prescription data if index is empty"
    )
    args = parser.parse_args()
    
    success = asyncio.run(setup_elasticsearch(create_sample_data=args.sample_data))
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()