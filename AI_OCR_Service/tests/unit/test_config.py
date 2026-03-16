"""
Unit tests for configuration validation (Simplified for HF PaddleOCR).

Tests the Settings class and validation methods without requiring external services.
"""
import pytest
from unittest.mock import patch, MagicMock
from app.core.config.config import Settings, settings


class TestSettingsValidation:
    """Test configuration validation methods."""

    def test_get_masked_key_with_short_value(self):
        """Test masking short API keys."""
        # Use a key that still exists, like HF_API_KEY or GEMINI_API_KEY
        with patch.object(settings, 'HF_API_KEY', "short"):
            result = settings.get_masked_key('HF_API_KEY')
            assert result == "***"

    def test_get_masked_key_with_long_value(self):
        """Test masking long API keys."""
        with patch.object(settings, 'HF_API_KEY', "hf_abc123def456ghi789"):
            result = settings.get_masked_key('HF_API_KEY')
            assert result == "hf_a...i789"
            assert "..." in result
            assert len(result) < len("hf_abc123def456ghi789")

    def test_get_masked_key_not_set(self):
        """Test masking when key is not set."""
        with patch.object(settings, 'HF_API_KEY', None):
            result = settings.get_masked_key('HF_API_KEY')
            assert result == "NOT SET"

    def test_validate_required_settings_all_present(self):
        """Test validation when required keys are present."""
        with patch.object(settings, 'HF_API_KEY', "test-key-123"):
            result = settings.validate_required_settings(["HF_API_KEY"])
            assert result["HF_API_KEY"] is True

    def test_validate_required_settings_missing(self):
        """Test validation when required keys are missing."""
        with patch.object(settings, 'HF_API_KEY', None):
            result = settings.validate_required_settings(["HF_API_KEY"])
            assert result["HF_API_KEY"] is False

    def test_validate_ocr_providers_hf_enabled(self):
        """Test OCR provider validation with HF PaddleOCR enabled."""
        with patch.object(settings, 'HF_PADDLE_OCR_ENDPOINT_URL', "https://endpoint.hf.space"), \
             patch.object(settings, 'HF_API_KEY', "test-key"):
            result = settings.validate_ocr_providers()
            assert result["hf_paddle_ocr"]["enabled"] is True
            assert result["hf_paddle_ocr"]["key_configured"] is True

    def test_validate_ocr_providers_hf_disabled(self):
        """Test OCR provider validation with HF PaddleOCR disabled."""
        with patch.object(settings, 'HF_PADDLE_OCR_ENDPOINT_URL', None):
            result = settings.validate_ocr_providers()
            assert result["hf_paddle_ocr"]["enabled"] is False

    def test_get_validation_report_complete(self):
        """Test complete validation report generation."""
        with patch.object(settings, 'HF_API_KEY', "test-key"), \
             patch.object(settings, 'HF_PADDLE_OCR_ENDPOINT_URL', "https://endpoint.hf.space"), \
             patch.object(settings, 'ANTHROPIC_API_KEY', "test-key"), \
             patch.object(settings, 'ELASTICSEARCH_ENABLED', True):
            
            report = settings.get_validation_report()
            
            assert "ocr_providers" in report
            assert "extraction_providers" in report
            assert report["ocr_providers"]["at_least_one_available"] is True
            assert report["overall_status"] == "ok"