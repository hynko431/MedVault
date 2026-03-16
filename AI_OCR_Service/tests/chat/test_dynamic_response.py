"""
Test script to verify dynamic response formatting.
Tests that null/empty values are excluded from the response.
"""

import sys
import json
from pathlib import Path

# Add the AI_OCR_Service to path
sys.path.insert(0, str(Path(__file__).parent.parent / "AI_OCR_Service"))

from app.api.ocr import remove_none_and_empty_values

def test_remove_none_values():
    """Test that None values are removed"""
    test_data = {
        "patient": {
            "name": "Rina Paul",
            "age": "49",
            "gender": "F",
            "phone": None,
            "email": None,
            "address": None,
            "patient_id": None,
        },
        "doctor": {
            "names": ["Dr. Smith"],
            "qualifications": ["MBBS"],
            "registration_numbers": None,  # This will be removed
        },
        "medicines": [
            {
                "name": "Aspirin",
                "dosage": "500mg",
                "frequency": "1-0-1",
                "duration": "30 days",
                "instructions": None,  # None values in list items
            },
            {
                "name": None,  # This item will be filtered out
                "dosage": None,
            }
        ],
        "hospital": None,
        "follow_up": "2 weeks",
    }
    
    result = remove_none_and_empty_values(test_data)
    
    print("Original data:")
    print(json.dumps(test_data, indent=2))
    print("\n" + "="*60 + "\n")
    print("Cleaned data (None and empty values removed):")
    print(json.dumps(result, indent=2))
    
    # Assertions
    assert "phone" not in result["patient"], "None values should be removed from patient"
    assert result["patient"]["name"] == "Rina Paul", "Non-null values should be kept"
    assert "hospital" not in result, "None values at top level should be removed"
    assert "registration_numbers" not in result["doctor"], "None in nested dicts should be removed"
    assert len(result["medicines"]) == 1, "Empty medicine entries should be filtered out"
    assert "instructions" not in result["medicines"][0], "None in list items should be removed"
    
    print("\n" + "="*60)
    print("✅ All tests passed! Dynamic response formatting works correctly.")
    return result

if __name__ == "__main__":
    result = test_remove_none_values()
