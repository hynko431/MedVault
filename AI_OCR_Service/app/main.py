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
            "google_creds_set": bool(settings.GOOGLE_APPLICATION_CREDENTIALS),
            "providers": {
                "anthropic": {
                    "set": bool(settings.ANTHROPIC_API_KEY),
                    "preview": settings.get_masked_key("ANTHROPIC_API_KEY"),
                    "model": settings.ANTHROPIC_MODEL
                },
                "openrouter": {
                    "set": bool(settings.OPENROUTER_API_KEY),
                    "preview": settings.get_masked_key("OPENROUTER_API_KEY"),
                    "model": settings.OPENROUTER_MODEL
                },
                "groq": {
                    "set": bool(settings.GROQ_API_KEY),
                    "preview": settings.get_masked_key("GROQ_API_KEY"),
                    "model": settings.GROQ_MODEL
                }
            }
        }
    }

app.include_router(ocr_router, prefix="/ocr")