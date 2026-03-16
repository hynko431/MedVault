"""
AI OCR Service Test Suite.

This package contains all tests for the AI OCR Service application.
Tests are organized by functionality and include unit, integration,
and end-to-end tests.

Test Organization:
    tests/
    ├── __init__.py
    ├── test_imports.py       # General import tests
    ├── ocr/                 # OCR-related tests
    │   ├── test_enhanced_cleaner.py
    │   ├── test_frequency_patterns.py
    │   └── test_ocr_endpoint.py
    ├── es/                  # Elasticsearch tests
    │   ├── test_es_basic.py
    │   ├── test_es_connection.py
    │   ├── test_search_functionality.py
    │   └── test_dynamic_schema.py
    ├── chat/                # Chat/RAG tests
    │   ├── test_rag.py
    │   └── test_dynamic_response.py
    ├── utils/               # Utility scripts
    │   ├── debug_gemini.py
    │   └── ocr_cleaner_enhanced.py
    └── search/              # Search-related tests
        └── kibana_search_tests.http

Running Tests:
    # Run all tests
    >>> pytest tests/
    
    # Run specific category
    >>> pytest tests/ocr/
    >>> pytest tests/es/
    >>> pytest tests/chat/
    
    # Run specific test file
    >>> pytest tests/ocr/test_ocr_endpoint.py
    
    # Run with coverage
    >>> pytest tests/ --cov=AI_OCR_Service.app --cov-report=html

Fixtures:
    - client: FastAPI test client
    - settings: Test configuration
    - mock_ocr_response: Sample OCR data
"""

import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

# Ensure the AI_OCR_Service package is in the path
# This allows tests to run from any working directory
_project_root = Path(__file__).parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

# Test configuration constants
TEST_CONFIG = {
    "ELASTICSEARCH_ENABLED": False,
    "ELASTICSEARCH_HOST": "http://localhost:9200",
    "GOOGLE_APPLICATION_CREDENTIALS": None,
    "GEMINI_API_KEY": None,
    "ANTHROPIC_API_KEY": None,
    "OPENROUTER_API_KEY": None,
    "GROQ_API_KEY": None,
    "TESTING": True,
}


def get_test_data_path(filename: str) -> Path:
    """
    Get the absolute path to a test data file.
    
    Args:
        filename: Name of the test data file
        
    Returns:
        Path: Absolute path to the test data file
        
    Example:
        >>> from tests import get_test_data_path
        >>> path = get_test_data_path("sample_prescription.jpg")
    """
    return Path(__file__).parent / "data" / filename


def load_test_image(filename: str = "sample_prescription.jpg") -> bytes:
    """
    Load a test image file as bytes.
    
    Args:
        filename: Name of the image file in tests/data/
        
    Returns:
        bytes: Image file contents
        
    Raises:
        FileNotFoundError: If the image file doesn't exist
        
    Example:
        >>> image_bytes = load_test_image("prescription.jpg")
        >>> response = client.post("/ocr/extract", json={"image_url": "data:image/jpeg;base64,..."})
    """
    image_path = get_test_data_path(filename)
    if not image_path.exists():
        # Return a minimal valid JPEG placeholder for tests
        # This is a 1x1 pixel JPEG image
        return bytes([
            0xFF, 0xD8, 0xFF, 0xE0, 0x00, 0x10, 0x4A, 0x46, 0x49, 0x46,
            0x00, 0x01, 0x01, 0x00, 0x00, 0x01, 0x00, 0x01, 0x00, 0x00,
            0xFF, 0xD9
        ])
    
    with open(image_path, "rb") as f:
        return f.read()


def create_mock_ocr_response(
    medicine_name: str = "Paracetamol",
    dosage: str = "500mg",
    frequency: str = "BD"
) -> Dict[str, Any]:
    """
    Create a mock OCR extraction response for testing.
    
    Args:
        medicine_name: Name of the medicine
        dosage: Dosage amount
        frequency: Frequency of intake
        
    Returns:
        dict: Mock OCR response data
        
    Example:
        >>> from tests import create_mock_ocr_response
        >>> mock_data = create_mock_ocr_response("Ibuprofen", "400mg", "TID")
    """
    return {
        "prescription_id": "test-123",
        "status": "success",
        "extracted_data": {
            "patient": {
                "name": "Test Patient",
                "age": 35,
                "gender": "Male"
            },
            "doctor": {
                "name": "Dr. Test Doctor",
                "specialization": "General Physician"
            },
            "hospital": {
                "name": "Test Hospital",
                "address": "123 Test Street"
            },
            "medicines": [
                {
                    "name": medicine_name,
                    "dosage": dosage,
                    "frequency": frequency,
                    "duration": "7 days",
                    "instructions": "After food"
                }
            ],
            "diagnosis": ["Fever"],
            "date": "2024-01-15"
        },
        "extraction_mode": "dynamic",
        "fields_extracted": ["patient", "doctor", "medicines", "diagnosis"]
    }


def create_mock_search_result(
    user_id: str = "test-user-123",
    medicine_name: str = "Paracetamol"
) -> Dict[str, Any]:
    """
    Create a mock Elasticsearch search result for testing.
    
    Args:
        user_id: User ID for the search
        medicine_name: Medicine name in the result
        
    Returns:
        dict: Mock search result data
    """
    return {
        "total": 1,
        "page": 1,
        "page_size": 10,
        "results": [
            {
                "_id": "prescription-123",
                "_score": 1.5,
                "_source": {
                    "prescription_id": "prescription-123",
                    "user_id": user_id,
                    "doctor_name": "Dr. Test Doctor",
                    "hospital": "Test Hospital",
                    "medicine_names": [medicine_name],
                    "created_at": "2024-01-15T10:00:00Z"
                }
            }
        ]
    }


# Test utilities
class TestHelpers:
    """
    Utility class for test helper methods.
    """
    
    @staticmethod
    def is_elasticsearch_available() -> bool:
        """
        Check if Elasticsearch is available for integration tests.
        
        Returns:
            bool: True if ES is running and accessible
        """
        try:
            from app.core.config.config import settings
            
            if not settings.ELASTICSEARCH_ENABLED:
                return False
            
            from elasticsearch import Elasticsearch
            es = Elasticsearch(settings.ELASTICSEARCH_HOST)
            return es.ping()
        except Exception:
            return False
    
    @staticmethod
    def has_api_key(provider: str) -> bool:
        """
        Check if an API key is configured for a provider.
        
        Args:
            provider: Provider name ('gemini', 'anthropic', 'openrouter', 'groq')
            
        Returns:
            bool: True if API key is available
        """
        from app.core.config.config import settings
        
        key_mapping = {
            "gemini": settings.GEMINI_API_KEY,
            "anthropic": settings.ANTHROPIC_API_KEY,
            "openrouter": settings.OPENROUTER_API_KEY,
            "groq": settings.GROQ_API_KEY,
        }
        
        return bool(key_mapping.get(provider.lower()))


# Exports
__all__ = [
    # Test data utilities
    "get_test_data_path",
    "load_test_image",
    "create_mock_ocr_response",
    "create_mock_search_result",
    
    # Test configuration
    "TEST_CONFIG",
    
    # Test helpers
    "TestHelpers",
]
