"""
Unit tests for vision OCR module (Restored Fallback with HF Priority).
"""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
import asyncio

from app.services.ocr.vision_ocr import (
    UnifiedOCRError,
    retry_with_backoff,
    extract_text_with_fallback,
)

class TestExtractTextWithFallback:
    """Test extract_text_with_fallback function (Restored Chain)."""

    @pytest.mark.asyncio
    async def test_gemini_primary_success(self):
        """Test Gemini as 1st priority success."""
        mock_text = "Gemini Text"
        with patch('app.services.ocr.vision_ocr._try_gemini', new_callable=AsyncMock) as mock_gemini:
            mock_gemini.return_value = mock_text
            result = await extract_text_with_fallback(b"fake_image_bytes")
            assert result == mock_text
            mock_gemini.assert_called_once()

    @pytest.mark.asyncio
    async def test_google_vision_secondary_success(self):
        """Test Google Vision as 2nd priority success."""
        mock_text = "Vision Text"
        with patch('app.services.ocr.vision_ocr._try_gemini', new_callable=AsyncMock) as mock_gemini, \
             patch('app.services.ocr.vision_ocr._try_google_vision', new_callable=AsyncMock) as mock_vision:
            mock_gemini.side_effect = Exception("Gemini fails")
            mock_vision.return_value = mock_text
            result = await extract_text_with_fallback(b"fake_image_bytes")
            assert result == mock_text
            mock_vision.assert_called_once()

    @pytest.mark.asyncio
    async def test_hf_paddle_tertiary_success(self):
        """Test HF PaddleOCR as 3rd priority success."""
        mock_text = "HF Paddle Text"
        with patch('app.services.ocr.vision_ocr._try_gemini', new_callable=AsyncMock) as mock_gemini, \
             patch('app.services.ocr.vision_ocr._try_google_vision', new_callable=AsyncMock) as mock_vision, \
             patch('app.services.ocr.vision_ocr._try_hf_paddle', new_callable=AsyncMock) as mock_hf, \
             patch('app.services.ocr.vision_ocr.settings') as mock_settings:
            mock_settings.HF_PADDLE_OCR_ENDPOINT_URL = 'https://fake-endpoint'
            mock_gemini.side_effect = Exception("Gemini fails")
            mock_vision.side_effect = Exception("Vision fails")
            mock_hf.return_value = mock_text
            result = await extract_text_with_fallback(b"fake_image_bytes")
            assert result == mock_text
            mock_hf.assert_called_once()

    @pytest.mark.asyncio
    async def test_local_paddle_fallback_success(self):
        """Test Local PaddleOCR as 4th priority success."""
        mock_text = "Local Paddle Text"
        with patch('app.services.ocr.vision_ocr._try_gemini', new_callable=AsyncMock) as mock_gemini, \
             patch('app.services.ocr.vision_ocr._try_google_vision', new_callable=AsyncMock) as mock_vision, \
             patch('app.services.ocr.vision_ocr._try_hf_paddle', new_callable=AsyncMock) as mock_hf, \
             patch('app.services.ocr.vision_ocr._try_paddle', new_callable=AsyncMock) as mock_paddle, \
             patch('app.services.ocr.vision_ocr.settings') as mock_settings:
            mock_settings.HF_PADDLE_OCR_ENDPOINT_URL = 'https://fake-endpoint'
            mock_gemini.side_effect = Exception("Gemini fails")
            mock_vision.side_effect = Exception("Vision fails")
            mock_hf.side_effect = Exception("HF fails")
            mock_paddle.return_value = mock_text
            result = await extract_text_with_fallback(b"fake_image_bytes")
            assert result == mock_text
            mock_paddle.assert_called_once()