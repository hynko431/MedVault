import os
from google.cloud import vision
from app.core.config import settings

class OCRError(Exception):
    pass

def extract_text_from_image(image_bytes: bytes) -> str:
    try:
        # 1️⃣ Validate Credentials Path
        creds_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        if not creds_path:
            raise OCRError("GOOGLE_APPLICATION_CREDENTIALS environment variable is not set.")
        
        if not os.path.exists(creds_path):
            # Instead of leaking the full path, we provide a helpful but safe message
            filename = os.path.basename(creds_path)
            raise OCRError(f"Google Cloud credential file '{filename}' not found at the configured path. Please check your .env file.")

        # 2️⃣ Initialize Client
        # ADC is picked up automatically from the environment variable
        client = vision.ImageAnnotatorClient()

        image = vision.Image(content=image_bytes)
        response = client.annotate_image({
            'image': image,
            'features': [{'type_': vision.Feature.Type.TEXT_DETECTION}],
        })

        if response.error.message:
            raise RuntimeError(response.error.message)
        
        texts = response.text_annotations
        if not texts:
            return ""
        
        # Full OCR text is always the first entry
        return texts[0].description
    
    except OCRError:
        # Re-raise OCRError as is
        raise
    except Exception as e:
        # Log the error here if logging is configured
        raise OCRError(f"Vision OCR failed: {str(e)}")
