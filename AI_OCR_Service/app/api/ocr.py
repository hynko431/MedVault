from fastapi import APIRouter, HTTPException, BackgroundTasks
from app.models.schemas import OCRRequest, OCRResponse
from app.services.image_downloader import download_image, ImageDownloadError
from app.services.google_vision_ocr import extract_text_from_image, OCRError
from app.services.ocr_cleaner import clean_ocr_text
from app.services.claude_extractor import extract_structured_data, validate_extracted_json
from app.services.search_indexer import index_prescription

from app.services.ai_prep import prepare_text_for_ai

from app.services.claude_extractor import extract_medicines, ClaudeExtractionError
from app.models.schemas import PrescriptionExtract
import json


router = APIRouter()

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
        
        # 3️⃣ Clean the OCR text
        cleaned_text = clean_ocr_text(raw_text)

        if not cleaned_text.strip():
            raise HTTPException(status_code=400, detail="No text could be extracted from the image.")
        
        # 4️⃣ Extract structured data using Claude
        extracted_json_text = extract_structured_data(cleaned_text)
        validated_data = validate_extracted_json(extracted_json_text)
        
        ai_ready_text = prepare_text_for_ai(cleaned_text)

        claude_raw = extract_medicines(ai_ready_text)

        structured_data = PrescriptionExtract.parse_obj(json.loads(claude_raw))

        # 5️⃣ ASYNC indexing for search
        background_tasks.add_task(
            index_prescription,
            request.prescription_id,
            validated_data.model_dump()
        )
        
        # 6️⃣ Determine status based on confidence
        status = (
            "needs_review"
            if validated_data.overall_confidence and validated_data.overall_confidence < 0.85
            else "success"
        )

        return {
            "prescription_id": request.prescription_id,
            "raw_text": raw_text,
            "cleaned_text": cleaned_text,
            # "extracted_data": validated_data.model_dump(),
            # "ai_ready_text": ai_ready_text,
            "structured_data": structured_data.dict()
        }
        # return OCRResponse(
        #     prescription_id=request.prescription_id,
        #     status=status,
        #     extracted_data=validated_data
        # )
    
    except ImageDownloadError as e:
        raise HTTPException(status_code=400, detail=f"Image download failed: {str(e)}")

    except OCRError as e:
        # The 502 error reported was due to Google Vision credentials not being found.
        # We keep the 502 status code as it correctly represents a gateway/upstream error.
        raise HTTPException(status_code=502, detail=str(e))

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OCR processing error: {str(e)}")
    
    except ClaudeExtractionError as e:
        raise HTTPException(status_code=502, detail=str(e))
