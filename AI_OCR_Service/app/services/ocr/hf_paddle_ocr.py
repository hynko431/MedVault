import httpx
import base64
import logging
from typing import Optional
from app.core.config.config import settings
from app.core.logging.async_logger import log_performance

logger = logging.getLogger(__name__)

class HFOCRError(Exception):
    """Custom exception for Hugging Face OCR errors."""
    pass


@log_performance("Service: HF PaddleOCR Extraction")
async def extract_text_with_hf_paddle(image_bytes: bytes) -> str:
    """
    Extract text from image using Hugging Face Inference Endpoint for PaddleOCR.
    
    Args:
        image_bytes: Raw image bytes
        
    Returns:
        Extracted text
        
    Raises:
        HFOCRError: If extraction fails or returns invalid data
    """
    if not settings.HF_PADDLE_OCR_ENDPOINT_URL or not settings.HF_API_KEY:
        raise HFOCRError("HF PaddleOCR Endpoint not configured")

    try:
        # Encode image to base64
        encoded_image = base64.b64encode(image_bytes).decode('utf-8')
        
        headers = {
            "Authorization": f"Bearer {settings.HF_API_KEY}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "inputs": encoded_image
        }
        
        logger.info(f"Calling HF Inference Endpoint: {settings.HF_PADDLE_OCR_ENDPOINT_URL}")
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                settings.HF_PADDLE_OCR_ENDPOINT_URL,
                headers=headers,
                json=payload
            )
            
            if response.status_code != 200:
                error_body = response.text
                logger.error(f"HF Endpoint returned error {response.status_code}: {error_body}")
                raise HFOCRError(f"HF Endpoint returned error {response.status_code}: {error_body}")
            
            result = response.json()
            
            # The handler returns [{"text": "..."}] based on our sample handler
            text = None
            if isinstance(result, list) and len(result) > 0:
                text = result[0].get("text", "")
            elif isinstance(result, dict):
                text = result.get("text", "")
            
            if text is None:
                raise HFOCRError("HF Endpoint returned invalid response format")
            
            if not isinstance(text, str) or not text.strip():
                raise HFOCRError("HF Endpoint returned empty text")
            
            return text

    except HFOCRError:
        # Re-raise HFOCRError as-is
        raise
    except Exception as e:
        logger.error(f"Error calling HF PaddleOCR Endpoint: {str(e)}")
        raise HFOCRError(f"HF PaddleOCR failed: {str(e)}") from e
    
    return ""
