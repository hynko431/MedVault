from fastapi import FastAPI
from app.core.config import settings
from app.api.ocr import router as ocr_router

app = FastAPI(title="AI OCR & Search Service")

@app.get("/health")
def health_check():
    return {
        "status": "ok", 
        "service": "ai-ocr-search",
        "config": {
            "anthropic_key_set": bool(settings.ANTHROPIC_API_KEY),
            "google_creds_set": bool(settings.GOOGLE_APPLICATION_CREDENTIALS),
            "anthropic_key_preview": settings.get_masked_key("ANTHROPIC_API_KEY")
        }
    }

app.include_router(ocr_router, prefix="/ocr")