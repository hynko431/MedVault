import logging
import time
from fastapi import APIRouter, HTTPException, BackgroundTasks
from app.models.schemas import OCRRequest
from app.services.image_downloader import download_image, ImageDownloadError
from app.services.google_vision_ocr import extract_text_from_image, OCRError
from app.services.ocr_cleaner import clean_ocr_text
from app.services.claude_extractor import extract_structured_data, validate_extracted_json
from app.services.search_indexer import index_prescription, get_indexed_prescription

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/extract")
def extract_prescription(request: OCRRequest, background_tasks: BackgroundTasks):
    """
    Full OCR pipeline:
    1. Download image from S3 (presigned URL)
    2. Extract raw text via Google Vision
    3. Clean the OCR output
    4. Structured extraction via Claude AI
    5. Async index into Elasticsearch
    """
    start_time = time.monotonic()
    prescription_id = request.prescription_id
    logger.info("Starting OCR pipeline for prescription_id=%s", prescription_id)

    try:
        # Step 1 — Download image
        image_bytes = download_image(str(request.image_url))
        logger.info("[%s] Image downloaded (%d bytes)", prescription_id, len(image_bytes))

        # Step 2 — Google Vision OCR
        raw_text = extract_text_from_image(image_bytes)
        logger.info("[%s] Raw text extracted (%d chars)", prescription_id, len(raw_text))

        # Step 3 — Clean OCR text
        cleaned_text = clean_ocr_text(raw_text)

        if not cleaned_text.strip():
            raise HTTPException(
                status_code=400,
                detail="No text could be extracted from the image."
            )

        # Step 4 — Claude structured extraction
        extracted_json = extract_structured_data(cleaned_text)
        validated_data = validate_extracted_json(extracted_json)
        logger.info("[%s] Structured data extracted successfully.", prescription_id)

        # Step 5 — Async Elasticsearch indexing
        background_tasks.add_task(
            index_prescription,
            prescription_id,
            validated_data.model_dump(),
        )

        elapsed_ms = int((time.monotonic() - start_time) * 1000)
        logger.info("[%s] OCR pipeline complete in %dms", prescription_id, elapsed_ms)

        return {
            "prescription_id": prescription_id,
            "raw_text": raw_text,
            "cleaned_text": cleaned_text,
            "extracted_data": validated_data.model_dump(),
            "processing_time_ms": elapsed_ms,
        }

    except ImageDownloadError as e:
        raise HTTPException(status_code=400, detail=f"Image download failed: {str(e)}")

    except OCRError as e:
        raise HTTPException(status_code=502, detail=str(e))

    except HTTPException:
        raise  # Re-raise FastAPI exceptions as-is

    except Exception as e:
        logger.exception("[%s] Unexpected OCR error.", prescription_id)
        raise HTTPException(status_code=500, detail=f"OCR processing error: {str(e)}")


@router.get("/status/{prescription_id}")
def get_ocr_status(prescription_id: str):
    """
    Check whether a prescription has been indexed in Elasticsearch.
    Used by frontend polling to know when OCR is complete.
    """
    doc = get_indexed_prescription(prescription_id)
    if doc is None:
        return {
            "prescription_id": prescription_id,
            "status": "PROCESSING",
            "message": "Prescription not yet indexed.",
        }
    return {
        "prescription_id": prescription_id,
        "status": "COMPLETE",
        "extracted_data": doc,
    }
