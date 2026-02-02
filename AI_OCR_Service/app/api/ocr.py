from fastapi import APIRouter, HTTPException, BackgroundTasks
from app.models.schemas import OCRRequest
from app.services.image_downloader import download_image, ImageDownloadError
from app.services.vision_ocr import extract_text_from_image, UnifiedOCRError
from app.services.ocr_cleaner import clean_ocr_text
from app.services.claude_extractor import extract_structured_data, validate_extracted_json
from app.services.search_indexer import index_prescription

from app.services.ai_prep import prepare_text_for_ai
from app.core.disclaimer import MEDICAL_DISCLAIMER
import json
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/extract")
async def extract_prescription(request: OCRRequest, background_tasks: BackgroundTasks):
    """
    Extract structured data from prescription images using OCR and AI
    Returns the exact JSON structure requested by the user.
    
    OCR Fallback Pipeline:
    1. Gemini 3.0 Flash (GEMINI_API_KEY) - Primary, fastest
    2. Google Cloud Vision (GOOGLE_APPLICATION_CREDENTIALS) - Secondary, most accurate
    3. TrOCR - Tertiary, local fallback
    
    If all OCR providers fail, returns HTTP 502 (Bad Gateway).
    """
    try:
        # 1️⃣ Download image from S3
        image_bytes = download_image(str(request.image_url))

        # 2️⃣ OCR with Fallback Pipeline (Gemini → Google Vision → TrOCR)
        raw_text = extract_text_from_image(image_bytes)

        # 3️⃣ Clean the OCR text
        cleaned_text = clean_ocr_text(raw_text)

        if not cleaned_text.strip():
            raise HTTPException(status_code=400, detail="No text could be extracted from the image.")

        # 4️⃣ Extract structured data using Claude
        extracted_json_text = extract_structured_data(cleaned_text)
        validated_data = validate_extracted_json(extracted_json_text)

        ai_ready_text = prepare_text_for_ai(cleaned_text)

        # 5️⃣ ASYNC indexing for search
        background_tasks.add_task(
            index_prescription,
            request.prescription_id,
            validated_data.model_dump()
        )

        # 6️⃣ Determine status based on confidence
        # status = (
        #     "needs_review"
        #     if validated_data.overall_confidence and validated_data.overall_confidence < 0.85
        #     else "success"
        # )

        #3 return validated_data.model_dump()

        #1 return {
        #     "prescription_id": request.prescription_id,
        #     "raw_text": raw_text,
        #     "cleaned_text": cleaned_text,
        #     # "extracted_data": validated_data.model_dump(),
        #     "ai_ready_text": ai_ready_text
        # }
        #2 return OCRResponse(
        #     prescription_id=request.prescription_id,
        #     status=status,
        #     extracted_data=validated_data
        # )
        return {
            "prescription_id": request.prescription_id,
            "structured_data": validated_data.model_dump(),
            # "disclaimer": MEDICAL_DISCLAIMER
        }
    except ImageDownloadError as e:
        raise HTTPException(
            status_code=400, detail=f"Image download failed: {str(e)}"
        ) from e

    except UnifiedOCRError as e:
        # 502 error represents upstream/gateway failure (all OCR providers down)
        logger.error(f"OCR pipeline failed - all providers exhausted: {str(e)}")
        raise HTTPException(status_code=502, detail=str(e)) from e

    except Exception as e:
        # Log the error for debugging
        logger.error(f"OCR processing error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"OCR processing error: {str(e)}"
        ) from e
