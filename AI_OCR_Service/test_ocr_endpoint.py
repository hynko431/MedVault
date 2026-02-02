#!/usr/bin/env python3
"""
Test script for the OCR API endpoint.
This demonstrates how to call the exposed /ocr/extract endpoint from a backend client.
"""

import requests
import json
from typing import Optional

# OCR Service Configuration
OCR_SERVICE_URL = "http://127.0.0.1:8000"
OCR_ENDPOINT = f"{OCR_SERVICE_URL}/ocr/extract"

def test_ocr_extraction(
    prescription_id: str,
    image_url: str,
    user_id: Optional[str] = None
) -> dict:
    """
    Call the OCR API endpoint to extract prescription data.
    
    This is the backend client approach mentioned in the requirements:
    - You don't need the Google service account credentials in your backend code
    - You call this endpoint which handles all credential management internally
    - The results are returned for storage in your database
    
    Args:
        prescription_id: Unique ID for the prescription
        image_url: URL of the prescription image to process
        user_id: Optional user identifier
    
    Returns:
        Dictionary containing extracted prescription data or error details
    """
    
    payload = {
        "prescription_id": prescription_id,
        "image_url": image_url,
    }
    
    if user_id:
        payload["user_id"] = user_id
    
    try:
        response = requests.post(
            OCR_ENDPOINT,
            json=payload,
            timeout=120  # 2 minutes for OCR processing
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✓ OCR Extraction Successful")
            print(f"  Prescription ID: {result.get('prescription_id')}")
            print(f"  OCR Text: {result.get('ocr_text')[:100]}..." if result.get('ocr_text') else "  OCR Text: N/A")
            print(f"  Extracted Data: {json.dumps(result.get('extracted_data'), indent=2)}")
            return result
        else:
            print(f"✗ OCR Extraction Failed (Status: {response.status_code})")
            print(f"  Error: {response.json().get('detail', response.text)}")
            return {"error": response.json().get('detail', response.text)}
    
    except requests.exceptions.Timeout:
        print("✗ Request timeout - OCR processing took too long")
        return {"error": "Request timeout"}
    except requests.exceptions.ConnectionError:
        print(f"✗ Could not connect to OCR service at {OCR_SERVICE_URL}")
        print("  Make sure the service is running: python -m uvicorn app.main:app")
        return {"error": "Connection failed"}
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        return {"error": str(e)}


def test_health_check():
    """Test if the service is alive"""
    try:
        response = requests.get(f"{OCR_SERVICE_URL}/health", timeout=5)
        if response.status_code == 200:
            print("✓ Service health check passed")
            return True
        else:
            print(f"✗ Service health check failed: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print(f"✗ Cannot connect to service at {OCR_SERVICE_URL}")
        return False


if __name__ == "__main__":
    print("=" * 70)
    print("OCR API Endpoint Test")
    print("=" * 70)
    print()
    
    # Test 1: Health check
    print("Test 1: Health Check")
    print("-" * 70)
    if not test_health_check():
        print("\nService is not running. Start it with:")
        print("  cd AI_OCR_Service")
        print("  set PYTHONPATH=.")
        print("  python -m uvicorn app.main:app --host 127.0.0.1 --port 8000")
        exit(1)
    print()
    
    # Test 2: OCR Extraction (with sample image URL)
    print("Test 2: OCR Extraction")
    print("-" * 70)
    print("Note: Replace the image_url with an actual prescription image URL")
    print()
    
    # Example with a placeholder image URL
    sample_prescription_id = "RX-12345"
    sample_image_url = "https://via.placeholder.com/400x300?text=Sample+Prescription"
    
    print(f"Testing OCR extraction for prescription: {sample_prescription_id}")
    print(f"Image URL: {sample_image_url}")
    print()
    
    result = test_ocr_extraction(
        prescription_id=sample_prescription_id,
        image_url=sample_image_url,
        user_id="user-001"
    )
    print()
    
    # Test 3: API Documentation
    print("Test 3: API Documentation")
    print("-" * 70)
    print(f"Swagger UI available at: {OCR_SERVICE_URL}/docs")
    print(f"ReDoc available at: {OCR_SERVICE_URL}/redoc")
    print()
    
    print("=" * 70)
    print("IMPORTANT: Regarding the requirement 'No Direct Service Account Usage'")
    print("=" * 70)
    print("""
The /ocr/extract endpoint is now exposed as an API that handles:
- All Google Cloud credential management internally
- Multi-provider fallback (Google Vision → Gemini → TrOCR)
- Automatic retries with exponential backoff
- Error handling and logging

Your backend code:
1. Does NOT need Google service account credentials
2. Does NOT need API keys in environment variables
3. Simply calls the /ocr/extract endpoint with an image URL
4. Receives structured extracted prescription data

This architecture allows:
- Separation of concerns (credential management in one place)
- Easier deployment (backends don't need credentials)
- Better security (credentials not distributed everywhere)
- Centralized monitoring and logging
    """)
