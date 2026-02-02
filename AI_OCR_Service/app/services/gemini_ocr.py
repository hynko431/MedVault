import requests
import base64
import logging
from app.core.config import settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class GeminiOCRError(Exception):
    """Raised when Gemini OCR extraction fails"""
    pass


def extract_text_with_gemini(image_bytes: bytes, timeout: int = 20) -> str:
    """
    Extract text from image using Gemini 3.0 Flash (Secondary OCR Provider).
    
    Args:
        image_bytes: Raw image bytes to extract text from
        timeout: Request timeout in seconds
        
    Returns:
        Extracted text from the image
        
    Raises:
        GeminiOCRError: When extraction fails
    """
    if not settings.GEMINI_API_KEY:
        logger.error("GEMINI_API_KEY not set in environment")
        raise GeminiOCRError(
            "GEMINI_API_KEY not configured. "
            "Please add GEMINI_API_KEY to your .env file."
        )

    logger.info(f"Attempting OCR with {settings.GEMINI_MODEL}...")
    
    try:
        # Gemini API endpoint for vision
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{settings.GEMINI_MODEL}:generateContent?key={settings.GEMINI_API_KEY}"
        
        # Prepare the image for the request
        image_base64 = base64.b64encode(image_bytes).decode('utf-8')
        
        payload = {
            "contents": [
                {
                    "parts": [
                        {
                            "text": "Extract all text from this medical prescription image. "
                                   "Return only the extracted text, maintaining the layout as much as possible. "
                                   "Do not add any commentary or explanations."
                        },
                        {
                            "inline_data": {
                                "mime_type": "image/jpeg",
                                "data": image_base64
                            }
                        }
                    ]
                }
            ]
        }
        
        logger.debug(f"Sending request to Gemini API (timeout={timeout}s)...")
        response = requests.post(url, json=payload, timeout=timeout)
        
        if response.status_code != 200:
            error_detail = response.text
            logger.error(f"Gemini API error: {response.status_code} - {error_detail}")
            raise GeminiOCRError(
                f"Gemini API returned status {response.status_code}\n"
                f"Response: {error_detail}"
            )
            
        result = response.json()
        
        # Extract text from response
        try:
            extracted_text = result['candidates'][0]['content']['parts'][0]['text']
            logger.info(f"✅ Gemini OCR successful. Extracted {len(extracted_text)} characters.")
            return extracted_text.strip()
        except (KeyError, IndexError, TypeError) as e:
            logger.error(f"Failed to parse Gemini response: {str(e)} | Response: {result}")
            raise GeminiOCRError(
                f"Unexpected response format from Gemini API: {str(e)}\n"
                f"Response: {result}"
            )
            
    except requests.exceptions.Timeout:
        raise GeminiOCRError(f"Gemini request timed out after {timeout}s")
    except requests.exceptions.RequestException as e:
        logger.error(f"Gemini request failed: {str(e)}")
        raise GeminiOCRError(f"Network error during Gemini OCR: {str(e)}")
    except GeminiOCRError:
        # Re-raise GeminiOCRError as-is
        raise
    except Exception as e:
        logger.error(f"Unexpected error in Gemini OCR: {str(e)}", exc_info=True)
        raise GeminiOCRError(f"Gemini OCR failed: {str(e)}") from e