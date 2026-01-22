from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.vision_ocr import download_image
from app.services.google_vision_ocr import extract_text_from_image, OCRError

from app.services.ocr_cleaner import clean_ocr_text

from app.services.claude_extractor import extract_structured_data, validate_extracted_json

from fastapi import BackgroundTasks
from app.services.search_indexer import index_prescription

from app.models.schemas import OCRRequest
from app.services.image_downloader import download_image, ImageDownloadError

router = APIRouter()

# class OCRRequest(BaseModel):
#     prescription_id: str
#     image_url: str


from app.services.claude_extractor import (
    extract_structured_data,
    validate_extracted_json
)

@router.post("/extract")
def extract_prescription(request: OCRRequest, background_tasks: BackgroundTasks):
    """
    Extract structured data from prescription images using OCR and AI
    """
    try:
        # 1️⃣ Download image from S3
        image_bytes = download_image(str(request.image_url))
        
        # 2️⃣ OCR using Google Vision (ADC)- Extract text using Google Vision OCR 
        raw_text = extract_text_from_image(image_bytes)

        # return {
        #     "prescription_id": request.prescription_id,
        #     "raw_text": raw_text
        # }
        
        # Clean the OCR text
        cleaned_text = clean_ocr_text(raw_text)
        
        # Extract structured data using Claude
        extracted_json_text = extract_structured_data(cleaned_text)
        validated_data = validate_extracted_json(extracted_json_text)
        
        # ASYNC indexing for search
        background_tasks.add_task(
            index_prescription,
            request.prescription_id,
            validated_data.model_dump()
        )
        
        return {
            "prescription_id": request.prescription_id,
            "raw_text": raw_text,
            "cleaned_text": cleaned_text,
            "extracted_data": validated_data.model_dump()
        }
    
    except ImageDownloadError as e:
        raise HTTPException(status_code=400, detail=f"Image download failed: {str(e)}")

    except OCRError as e:
        raise HTTPException(status_code=502, detail=str(e))

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OCR processing error: {str(e)}")
