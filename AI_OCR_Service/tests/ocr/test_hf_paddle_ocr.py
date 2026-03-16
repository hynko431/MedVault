import pytest
import asyncio
from unittest.mock import AsyncMock, patch
from app.services.ocr.hf_paddle_ocr import extract_text_with_hf_paddle
from app.core.config.config import settings

from unittest.mock import AsyncMock, patch, MagicMock

@pytest.mark.asyncio
async def test_extract_text_with_hf_paddle_success():
    """Test successful OCR extraction from HF Endpoint."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = [{"text": "Sample Prescription Text"}]
    
    # httpx.AsyncClient.post is a coroutine
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_response
        with patch.object(settings, "HF_PADDLE_OCR_ENDPOINT_URL", "https://mockbox.hf.space"):
            with patch.object(settings, "HF_API_KEY", "mock_key"):
                text = await extract_text_with_hf_paddle(b"fake_image_bytes")
                assert text == "Sample Prescription Text"

@pytest.mark.asyncio
async def test_extract_text_with_hf_paddle_failure():
    """Test handling of HF Endpoint failure."""
    mock_response = AsyncMock()
    mock_response.status_code = 500
    mock_response.text = "Internal Server Error"
    
    with patch("httpx.AsyncClient.post", return_value=mock_response):
        with patch.object(settings, "HF_PADDLE_OCR_ENDPOINT_URL", "https://mockbox.hf.space"):
            with patch.object(settings, "HF_API_KEY", "mock_key"):
                text = await extract_text_with_hf_paddle(b"fake_image_bytes")
                assert text is None

@pytest.mark.asyncio
async def test_extract_text_with_hf_paddle_not_configured():
    """Test when settings are missing."""
    with patch.object(settings, "HF_PADDLE_OCR_ENDPOINT_URL", None):
        text = await extract_text_with_hf_paddle(b"fake_image_bytes")
        assert text is None
