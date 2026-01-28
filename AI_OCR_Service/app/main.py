import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from app.api.chat import router as chat_router

from app.api.ocr import router as ocr_router
from app.api.search import router as search_router
from app.core.config import settings
from app.services.search_indexer import create_prescriptions_index

# Configure logging
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manage application lifespan events (startup and shutdown).
    This replaces the deprecated @app.on_event("startup") decorator.
    """
    # Startup: Initialize resources
    logger.info("Starting up AI OCR & Search Service...")
    try:
        create_prescriptions_index("v2")
        logger.info("Elasticsearch index initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize Elasticsearch index: {e}")
        # Continue anyway - the service can still work without Elasticsearch

    yield  # Application is running

    # Shutdown: Clean up resources
    logger.info("Shutting down AI OCR & Search Service...")
    # Add cleanup code here if needed (e.g., close_db_connection())


# Initialize FastAPI app with lifespan context manager
app = FastAPI(
    title="AI OCR & Search Service",
    description="Service for OCR extraction and prescription search",
    version="1.0.0",
    lifespan=lifespan
)


@app.get("/health")
async def health_check():
    """
    Health check endpoint that returns service status and configuration info.
    
    Returns:
        dict: Service status and configuration details
    """
    return {
        "status": "ok", 
        "service": "ai-ocr-search",
        "config": {
            "google_creds_set": bool(settings.GOOGLE_APPLICATION_CREDENTIALS),
            "elasticsearch_enabled": settings.ELASTICSEARCH_ENABLED,
            "providers": {
                "anthropic": {
                    "enabled": bool(settings.ANTHROPIC_API_KEY),
                    "preview": settings.get_masked_key("ANTHROPIC_API_KEY"),
                    "model": settings.ANTHROPIC_MODEL
                },
                "openrouter": {
                    "enabled": bool(settings.OPENROUTER_API_KEY),
                    "preview": settings.get_masked_key("OPENROUTER_API_KEY"),
                    "model": settings.OPENROUTER_MODEL
                },
                "groq": {
                    "enabled": bool(settings.GROQ_API_KEY),
                    "preview": settings.get_masked_key("GROQ_API_KEY"),
                    "model": settings.GROQ_MODEL
                }
            }
        }
    }


# Include API routers
app.include_router(ocr_router, prefix="/ocr", tags=["OCR"])
app.include_router(search_router, prefix="/search", tags=["Search"])
app.include_router(chat_router, prefix="/chat")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )
