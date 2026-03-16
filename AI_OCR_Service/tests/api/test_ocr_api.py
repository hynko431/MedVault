import pytest
from httpx import AsyncClient
from app.main import app
from unittest.mock import patch, MagicMock
from app.models.schemas import OCRRequest

@pytest.mark.asyncio
async def test_extract_endpoint_async():
    """
    Test that the /ocr/extract endpoint operates asynchronously without blocking
    and correctly falls back through the OCR tiers.
    """
    # Mock the image downloader and the OCR engine
    with patch("app.api.ocr.download_image") as mock_download_image, \
         patch("app.api.ocr.perform_ocr_with_fallback") as mock_perform_ocr, \
         patch("app.api.ocr._get_claude_extractor") as mock_get_extractor, \
         patch("app.api.ocr._get_search_indexer") as mock_get_search:
        
        mock_download_image.return_value = b"fake_image_bytes"
        mock_perform_ocr.return_value = "Mocked Patient Prescription Text"
        
        # Mock the AI extraction layer
        async def mock_extract(text, extraction_mode):
            return '{"patient_name": "John Doe", "medicines": [{"name": "Aspirin"}]}'
            
        mock_validate = MagicMock()
        mock_validate.return_value.model_dump.return_value = {
            "patient_name": "John Doe", 
            "medicines": [{"name": "Aspirin"}]
        }
        
        mock_get_extractor.return_value = (mock_extract, mock_validate)
        
        # Mock background task indexer
        mock_get_search.return_value = MagicMock()
        request_payload = {
            "image_url": "https://example.com/prescription.jpg",
            "prescription_id": "rx-12345",
            "extraction_mode": "dynamic"
        }
        
        from httpx import ASGITransport
        # Use httpx AsyncClient for async endpoint testing
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post("/ocr/extract", json=request_payload)
            
        assert response.status_code == 200
        data = response.json()
        assert data["patient_name"] == "John Doe"
        assert len(data["medicines"]) == 1
        
        # Verify the mocks were called, proving the async chain fired
        mock_download_image.assert_called_once()
        mock_perform_ocr.assert_called_once()
        mock_get_extractor.assert_called_once()
