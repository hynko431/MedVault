import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from app.core.config import settings
from app.api.ocr import router as ocr_router
from app.api.search import router as search_router

# ── Logging setup ─────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger(__name__)


# ── Lifespan (startup / shutdown hooks) ───────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── Startup ──────────────────────────────────────────────────────────────
    logger.info("Starting %s ...", settings.PROJECT_NAME)

    # 1. Validate Google credentials file is present
    creds_path = settings.GOOGLE_APPLICATION_CREDENTIALS
    if not creds_path or not os.path.exists(creds_path):
        logger.warning(
            "Google credentials file NOT found at '%s'. "
            "OCR requests will fail until this is resolved.",
            creds_path,
        )
    else:
        logger.info("Google credentials found at '%s'.", creds_path)

    # 2. Verify Anthropic API key is set
    if not settings.ANTHROPIC_API_KEY:
        logger.warning("ANTHROPIC_API_KEY is not set. Claude extraction will fail.")
    else:
        logger.info("Anthropic API key is configured.")

    # 3. Test Elasticsearch connectivity (warn only, never crash on ES)
    try:
        from app.services.search_indexer import get_es_client
        es = get_es_client()
        if es.ping():
            logger.info("Elasticsearch is reachable at %s.", settings.ELASTICSEARCH_HOST)
        else:
            logger.warning(
                "Elasticsearch ping failed at %s. "
                "Indexing will be silently skipped until ES is available.",
                settings.ELASTICSEARCH_HOST,
            )
    except Exception as e:
        logger.warning("Elasticsearch connectivity check failed: %s", str(e))

    logger.info("%s is ready on port %d.", settings.PROJECT_NAME, settings.API_PORT)

    yield  # ── Service is running ──────────────────────────────────────────

    # ── Shutdown ─────────────────────────────────────────────────────────────
    logger.info("Shutting down %s.", settings.PROJECT_NAME)


# ── FastAPI application ────────────────────────────────────────────────────────
app = FastAPI(
    title=settings.PROJECT_NAME,
    description=(
        "Microservice for extracting structured prescription data from images "
        "using Google Vision OCR + Claude AI, with Elasticsearch-powered search."
    ),
    version="0.2.0",
    lifespan=lifespan,
)


# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(ocr_router, prefix="/ocr", tags=["OCR"])
app.include_router(search_router, prefix="/search", tags=["Search"])


# ── Health endpoints ──────────────────────────────────────────────────────────
@app.get("/health", tags=["Health"])
def health_check():
    """Basic liveness probe — always returns OK if the service is up."""
    return {"status": "ok", "service": settings.PROJECT_NAME}


@app.get("/health/detailed", tags=["Health"])
def health_detailed():
    """
    Detailed readiness probe — checks credentials and Elasticsearch.
    Useful for Docker health-checks and ops dashboards.
    """
    import os
    from app.services.search_indexer import get_es_client

    creds_path = settings.GOOGLE_APPLICATION_CREDENTIALS
    creds_ok = bool(creds_path and os.path.exists(creds_path))

    try:
        es_ok = get_es_client().ping()
    except Exception:
        es_ok = False

    return {
        "status": "ok",
        "service": settings.PROJECT_NAME,
        "checks": {
            "google_credentials": "ok" if creds_ok else "missing",
            "anthropic_api_key": "ok" if settings.ANTHROPIC_API_KEY else "missing",
            "elasticsearch": "ok" if es_ok else "unreachable",
        },
    }