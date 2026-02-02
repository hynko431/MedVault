from fastapi import APIRouter, HTTPException, BackgroundTasks
import logging
from app.models.schemas import OCRRequest
from app.services.image_downloader import download_image, ImageDownloadError
from app.services.gemini_ocr import extract_text_with_gemini, GeminiOCRError
from app.services.google_vision_ocr import extract_text_from_image, OCRError
from app.services.trocr_service import extract_text_with_trocr, TrOCRError
from app.services.ocr_cleaner import clean_ocr_text
from app.services.claude_extractor import extract_structured_data, validate_extracted_json
from app.services.search_indexer import index_prescription

logger = logging.getLogger(__name__)
router = APIRouter()

def perform_ocr_with_fallback(image_bytes: bytes) -> str:
    """
    Orchestrates OCR with the requested priority:
    1. Gemini 3.0 Flash
    2. Google Vision OCR
    3. TrOCR (Transformer-Based HTR)
    """
    errors = []

    # 1. Gemini 3.0 Flash (Priority 1)
    try:
        return extract_text_with_gemini(image_bytes)
    except Exception as e:
        err = f"Gemini OCR failed: {str(e)}"
        logger.warning(err)
        errors.append(err)

    # 2. Google Vision OCR (Priority 2)
    try:
        return extract_text_from_image(image_bytes)
    except Exception as e:
        err = f"Google Vision OCR failed: {str(e)}"
        logger.warning(err)
        errors.append(err)

    # 3. TrOCR (Priority 3)
    try:
        return extract_text_with_trocr(image_bytes)
    except Exception as e:
        err = f"TrOCR failed: {str(e)}"
        logger.warning(err)
        errors.append(err)

    raise HTTPException(
        status_code=502, 
        detail=f"All OCR engines failed. Errors: {'; '.join(errors)}"
    )

@router.post("/extract")
def extract_prescription(request: OCRRequest, background_tasks: BackgroundTasks):
    """
    Extract structured data from prescription images using a multi-tier OCR engine
    and dynamic AI extraction fallback.
    """
    try:
        # 1️⃣ Download image
        image_bytes = download_image(str(request.image_url))
        
        # 2️⃣ OCR with 3-tier fallback (Gemini -> Google Vision -> TrOCR)
        raw_text = perform_ocr_with_fallback(image_bytes)
        
        # 3️⃣ Clean the OCR text
        cleaned_text = clean_ocr_text(raw_text)

        if not cleaned_text.strip():
            raise HTTPException(status_code=400, detail="No text could be extracted from the image.")
        
        # 4️⃣ Extract structured data using AI (Anthropic -> OpenRouter -> Groq fallback)
        # Uses the extraction_mode from the request (defaults to "dynamic")
        extraction_mode = getattr(request, 'extraction_mode', 'dynamic')
        extracted_json_text = extract_structured_data(cleaned_text, extraction_mode=extraction_mode)
        validated_data = validate_extracted_json(extracted_json_text)
        
        # 5️⃣ ASYNC indexing for search
        background_tasks.add_task(
            index_prescription,
            request.prescription_id,
            validated_data.model_dump()
        )
        
        # 6️⃣ Return the structured JSON
        return validated_data.model_dump()
    
    except HTTPException:
        raise
    except ImageDownloadError as e:
        raise HTTPException(status_code=400, detail=f"Image download failed: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected processing error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal processing error: {str(e)}")
