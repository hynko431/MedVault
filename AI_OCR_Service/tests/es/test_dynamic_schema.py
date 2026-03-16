"""
Test DynamicPrescriptionExtracted schema with Elasticsearch.
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "AI_OCR_Service"))

from app.core.config.config import settings
from app.services.search_indexer import AsyncSearchService, ElasticsearchClientFactory, DocumentBuilder


async def test_dynamic_schema():
    print("=" * 70)
    print("Testing with DynamicPrescriptionExtracted Schema")
    print("=" * 70)
    
    # Clear cached client
    ElasticsearchClientFactory._async_client = None
    
    # Sample data matching DynamicPrescriptionExtracted schema
    sample_prescription = {
        "prescription_id": "rx_dynamic_001",
        "user_id": "1",
        "patient": {
            "name": "John Doe",
            "age": 45,
            "gender": "Male",
            "blood_group": "O+"
        },
        "doctor": {
            "name": "Dr. Sarah Johnson",
            "names": ["Dr. Sarah Johnson", "Dr. S. Johnson"],
            "specialization": "Cardiologist",
            "qualifications": ["MD", "FACC"]
        },
        "hospital": {
            "name": "City Heart Center",
            "address": "123 Main St, New York"
        },
        "medicines": [
            {
                "name": "Paracetamol",
                "dosage": "500mg",
                "frequency": "Twice daily",
                "duration": "7 days",
                "form": "tablet"
            },
            {
                "name": "Atorvastatin",
                "dosage": "10mg",
                "frequency": "Once daily at night",
                "duration": "30 days",
                "form": "tablet"
            }
        ],
        "diagnosis": ["Hypertension", "High Cholesterol"],
        "symptoms": ["Chest pain", "Shortness of breath"],
        "advice": ["Take medications regularly", "Follow diet plan", "Exercise daily"],
        "date": "2026-02-13",
        "extraction_metadata": {
            "mode": "dynamic",
            "confidence": 0.95
        }
    }
    
    # Build document for indexing
    print("\n1. Building document from DynamicPrescriptionExtracted...")
    doc = DocumentBuilder.build_prescription_document(
        "rx_dynamic_001",
        sample_prescription,
        user_id="1"
    )
    
    print(f"   prescription_id: {doc['prescription_id']}")
    print(f"   doctor_name: {doc['doctor_name']}")
    print(f"   hospital: {doc['hospital']}")
    print(f"   patient_name: {doc['patient_name']}")
    print(f"   medicine_names: {doc['medicine_names']}")
    print(f"   diagnosis: {doc['diagnosis']}")
    print(f"   raw_text (first 100 chars): {doc['raw_text'][:100]}...")
    
    # Index and search
    print("\n2. Testing index and search...")
    service = AsyncSearchService()
    
    try:
        await service.index_document("rx_dynamic_001", doc)
        print("   Document indexed")
        
        await asyncio.sleep(1)  # Wait for indexing
        
        # Search for Paracetamol
        results = await service.search_medicine("Paracetamol", "1", size=10)
        if results:
            hits = results.get("hits", {}).get("hits", [])
            print(f"   Search 'Paracetamol': {len(hits)} results")
            for hit in hits:
                src = hit.get("_source", {})
                print(f"      - {src.get('prescription_id')}: {src.get('medicine_names')}")
        
        # Search for doctor
        results = await service.search_medicine("Sarah Johnson", "1", size=10)
        if results:
            hits = results.get("hits", {}).get("hits", [])
            print(f"   Search 'Sarah Johnson': {len(hits)} results")
            
    except Exception as e:
        print(f"   Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await service.close()
    
    print("\n" + "=" * 70)
    print("Dynamic schema test completed!")
    print("=" * 70)


if __name__ == "__main__":
    if not settings.ELASTICSEARCH_ENABLED:
        print("ERROR: ES is disabled!")
        sys.exit(1)
    
    asyncio.run(test_dynamic_schema())