from fastapi import FastAPI
from app.api.ocr import router as ocr_router

app = FastAPI(title="AI OCR & Search Service")

@app.get("/health")
def health_check():
    return {"status": "ok", "service": "ai-ocr-search"}

app.include_router(ocr_router, prefix="/ocr")