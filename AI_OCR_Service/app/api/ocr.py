from fastapi import APIRouter, HTTPException, BackgroundTasks, Request
from fastapi.responses import JSONResponse
import logging
from typing import Any, Dict

from app.models.schemas import OCRRequest
from app.services.ocr.image_downloader import download_image, ImageDownloadError
from app.services.ocr.ocr_cleaner import clean_ocr_text

# Explicit imports for core modules (replacing lazy package imports)
from app.core.logging.async_logger import log_performance
from app.core.utils.validation import ValidationError, validate_image_url, validate_prescription_id
from app.core.resilience.rate_limiter import rate_limiter, RateLimitType, RateLimitExceeded

logger = logging.getLogger(__name__)
router = APIRouter()

# Lazy-loaded heavy OCR and AI services
_vision_ocr = None
_claude_extractor = None
_search_indexer = None


def _get_vision_ocr():
    """Lazy load unified vision OCR service"""
    global _vision_ocr
    if _vision_ocr is None:
        from app.services.ocr import vision_ocr
        _vision_ocr = vision_ocr
    return _vision_ocr


def _get_claude_extractor():
    """Lazy load Claude extraction service"""
    global _claude_extractor
    if _claude_extractor is None:
        from app.services.chat.claude_extractor import extract_structured_data, validate_extracted_json
        _claude_extractor = (extract_structured_data, validate_extracted_json)
    return _claude_extractor


def _get_search_indexer():
    """Lazy load search indexer"""
    global _search_indexer
    if _search_indexer is None:
        from app.services.search.search_indexer import index_prescription
        _search_indexer = index_prescription
    return _search_indexer

def remove_none_and_empty_values(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Recursively remove None values and empty dictionaries from the response.
    This creates a truly dynamic response that only shows fields with actual values.
    
    Returns:
        Dictionary with None values and empty containers removed
    """
    if not isinstance(data, dict):
        return data
    
    cleaned: Dict[str, Any] = {}
    for key, value in data.items():
        # Skip None values
        if value is None:
            continue
        
        # Recursively clean dictionaries
        if isinstance(value, dict):
            cleaned_dict = remove_none_and_empty_values(value)
            # Only include non-empty dictionaries
            if cleaned_dict:
                cleaned[key] = cleaned_dict
        
        # Handle lists - keep them but recursively clean dict items within
        elif isinstance(value, list):
            if value:  # Only include non-empty lists
                cleaned_list = []
                for item in value:
                    if isinstance(item, dict):
                        cleaned_item = remove_none_and_empty_values(item)
                        if cleaned_item:  # Only add non-empty dicts
                            cleaned_list.append(cleaned_item)
                    elif item is not None:  # Skip None items in lists
                        cleaned_list.append(item)
                if cleaned_list:
                    cleaned[key] = cleaned_list
        
        # Keep all other non-None values
        else:
            cleaned[key] = value
    
    return cleaned

async def perform_ocr_with_fallback(image_bytes: bytes) -> str:
    """
    Orchestrates OCR with the requested priority using unified vision OCR service.
    1. Gemini 3.0 Flash
    2. Google Vision OCR
    3. PaddleOCR-VL (Transformer-Based OCR)
    """
    # Use lazy-loaded unified OCR service
    vision_ocr = _get_vision_ocr()
    return await vision_ocr.extract_text_with_fallback(image_bytes)


@router.post("/extract")
@log_performance("OCR Extract Endpoint")
async def extract_prescription(request: OCRRequest, background_tasks: BackgroundTasks, http_request: Request) -> Dict[str, Any]:
    """
    Extract structured data from prescription images using a multi-tier OCR engine
    and dynamic AI extraction fallback.
    
    Rate limited: 10 requests per minute with burst of 3
    """
    # Rate limiting check
    try:
        # Use client IP as rate limit key
        client_ip = http_request.client.host if http_request.client else "unknown"
        rate_result = await rate_limiter.check_rate_limit(client_ip, RateLimitType.OCR)
    except RateLimitExceeded as e:
        return JSONResponse(
            status_code=429,
            content={
                "error": "Rate limit exceeded",
                "message": str(e),
                "retry_after": e.retry_after,
                "limit": e.limit, # Added missing line from the instruction's implied context
                "reset_time": e.reset_time
            },
            headers=rate_limiter.get_rate_limit_headers({
                "limit": e.limit,
                "remaining": 0,
                "reset_time": e.reset_time
            })
        ) # type: ignore
    
    try:
        # 0️⃣ Validate inputs
        try:
            validate_image_url(str(request.image_url))
            if request.prescription_id and request.prescription_id != "unknown":
                validate_prescription_id(request.prescription_id)
        except ValidationError as e:
            raise HTTPException(status_code=400, detail=f"Validation error: {e.message}")
        
        # 1️⃣ Download image
        image_bytes = await download_image(str(request.image_url))
        
        # 2️⃣ OCR with 3-tier fallback (Gemini -> Google Vision -> PaddleOCR-VL)
        raw_text = await perform_ocr_with_fallback(image_bytes)
        
        # 3️⃣ Clean the OCR text
        cleaned_text = clean_ocr_text(raw_text)

        if not cleaned_text.strip():
            raise HTTPException(status_code=400, detail="No text could be extracted from the image.")
        
        # 4️⃣ Extract structured data using AI (Anthropic -> OpenRouter -> Groq fallback)
        # Uses the extraction_mode from the request (defaults to "dynamic")
        extract_func, validate_func = _get_claude_extractor()
        extraction_mode = getattr(request, 'extraction_mode', 'dynamic')
        extracted_json_text = await extract_func(cleaned_text, extraction_mode=extraction_mode)
        validated_data = validate_func(extracted_json_text)
        
        # 5️⃣ Serialize to dict and remove null/empty values for dynamic response
        response_data = validated_data.model_dump()
        dynamic_response = remove_none_and_empty_values(response_data)
        
        # 6️⃣ ASYNC indexing for search (use full data with nulls for indexing)
        index_func = _get_search_indexer()
        background_tasks.add_task(
            index_func,
            request.prescription_id or "unknown",
            response_data
        )
        
        # 7️⃣ Return the dynamic response (only non-null fields)
        return dynamic_response
    
    except HTTPException:
        raise
    except ImageDownloadError as e:
        raise HTTPException(status_code=400, detail=f"Image download failed: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected processing error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal processing error: {str(e)}")
