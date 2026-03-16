"""
Load environment variables BEFORE any LangChain imports.
This ensures LANGSMITH_API_KEY and other env vars are available 
when langchain modules are imported, preventing the warning:
"⚠️ LANGSMITH_API_KEY not set. Tracing disabled."
"""
from dotenv import load_dotenv
load_dotenv(override=True)

import asyncio
import os
import time
from contextlib import asynccontextmanager
from typing import Any, Optional, Dict, List, TYPE_CHECKING

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.middleware.cors import CORSMiddleware

# High-performance JSON Serialization and Compression
import orjson
from fastapi.responses import ORJSONResponse

# Define a custom ORJSONResponse that handles edge-case serializations like NumPy
class CustomORJSONResponse(ORJSONResponse):
    def render(self, content: Any) -> bytes:
        return orjson.dumps(
            content,
            option=orjson.OPT_NON_STR_KEYS | orjson.OPT_SERIALIZE_NUMPY | orjson.OPT_SERIALIZE_DATACLASS
        )

from app.core import get_settings, storage, monitoring
from app.core.logging.async_logger import get_async_logger
from app.core.db.elasticsearch import close_es_client
from app.core.db import elasticsearch
from app.core.storage.cache import check_redis_health
from app.core.monitoring.performance import latency_collector
settings = get_settings()
from app.services.search.search_indexer import es_service

# Configure logging early - use async logger for better performance
logger_instance = get_async_logger(__name__)

from app.api.chat import router as chat_router
from app.api.ocr import router as ocr_router
from app.api.search import router as search_router
from app.api.autocomplete import router as autocomplete_router


async def _init_elasticsearch(timeout: float = 30.0) -> bool:
    """
    Initialize Elasticsearch index in background.
    
    Args:
        timeout: Maximum time to wait for initialization in seconds
    
    Returns:
        bool: True if initialization succeeded, False otherwise
    """
    try:
        # Lazy import for ES index creation
        from app.services.search.search_indexer import create_prescriptions_index
        
        # Run synchronous index creation in thread pool
        loop = asyncio.get_running_loop()
        def _create_index(*args: Any, **kwargs: Any) -> Any:
            return create_prescriptions_index("v2")
        result = await asyncio.wait_for(
            loop.run_in_executor(None, _create_index),
            timeout=timeout
        )
        if result is not None:
            logger_instance.info("✅ Elasticsearch index initialized successfully")
            return True
        else:
            logger_instance.warning("⚠️ Elasticsearch index initialization returned None (ES may be down)")
            logger_instance.info("   Service will continue without Elasticsearch (search features disabled)")
            return False
    except asyncio.TimeoutError:
        logger_instance.warning(f"⚠️ Elasticsearch initialization timed out after {timeout}s")
        return False
    except Exception as e:
        logger_instance.warning(f"⚠️ Elasticsearch initialization failed: {e}")
        return False
    
    logger_instance.info("   Service will continue without Elasticsearch (search features disabled)")
    return False


async def _run_performance_cleanup() -> None:
    """Background task to clean up orphaned performance timers."""
    from app.core.monitoring.performance import performance_tracker
    while True:
        try:
            await asyncio.sleep(300)
            performance_tracker.cleanup_orphaned_timers(max_age_seconds=300)
        except asyncio.CancelledError:
            break


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manage application lifespan events (startup and shutdown).
    Optimized for fast startup - Elasticsearch initialization is non-blocking.
    """
    startup_start = time.time()
    es_task: Optional[asyncio.Task] = None
    perf_cleanup_task: Optional[asyncio.Task] = None
    
    try:
        logger_instance.info("🚀 Starting up AI OCR & Search Service...")
        
        # Check Elasticsearch health at startup
        if settings.ELASTICSEARCH_ENABLED:
            try:
                es_healthy = await es_service.health_check()
                if es_healthy:
                    logger_instance.info(f"✅ Elasticsearch connected at {settings.ES_HOST}")
                    # Only initialize index if ES is actually reachable
                    es_task = asyncio.create_task(_init_elasticsearch(), name="es_init")
                else:
                    logger_instance.warning(f"⚠️ Elasticsearch not reachable at {settings.ES_HOST}")
                    logger_instance.warning("   Service will continue without Elasticsearch (search features disabled)")
            except Exception as e:
                logger_instance.warning(f"⚠️ Elasticsearch connection failed: {e}")
                logger_instance.warning("   Service will continue without Elasticsearch (search features disabled)")
        else:
            logger_instance.info("📝 Elasticsearch is disabled in configuration")
            
        # Check Redis health at startup
        if getattr(settings, 'REDIS_ENABLED', False):
            try:
                redis_healthy = await check_redis_health()
                if redis_healthy:
                    logger_instance.info(f"✅ Redis connected and ready for caching")
                else:
                    logger_instance.warning(f"⚠️ Redis connection failed or not reachable")
            except Exception as e:
                logger_instance.warning(f"⚠️ Redis startup check error: {e}")
        
        # Record startup time immediately (don't wait for ES)
        startup_elapsed = time.time() - startup_start
        logger_instance.info(f"⚡ Fast startup complete in {startup_elapsed:.2f}s")
        
        # Start background performance cleanup task
        perf_cleanup_task = asyncio.create_task(_run_performance_cleanup(), name="perf_cleanup")
        
        yield  # Application is running
        
    finally:
        # Shutdown: Clean up resources
        logger_instance.info("🛑 Shutting down AI OCR & Search Service...")
        
        # Cancel background tasks if still running
        if es_task and not es_task.done():
            es_task.cancel()
            try:
                await asyncio.wait_for(es_task, timeout=1.0)
            except (asyncio.TimeoutError, asyncio.CancelledError):
                pass
        
        if perf_cleanup_task and not perf_cleanup_task.done():
            perf_cleanup_task.cancel()
            try:
                await asyncio.wait_for(perf_cleanup_task, timeout=1.0)
            except (asyncio.TimeoutError, asyncio.CancelledError):
                pass
        
        # Close Elasticsearch client (both from elasticsearch.py and search_indexer.py)
        await close_es_client()
        await es_service.close()
        logger_instance.info("✅ Elasticsearch connections closed")
        
        # Close cache connections (Redis and memory)
        from app.core.storage.cache import close_cache_manager
        await close_cache_manager()
        logger_instance.info("✅ Cache connections closed")


# Initialize FastAPI app with lifespan context manager
_settings = settings
app = FastAPI(
    title=_settings.PROJECT_NAME,
    version=_settings.VERSION,
    description="Backend service for MedVault AI OCR and intelligent search system",
    docs_url="/docs" if getattr(_settings, "ENVIRONMENT", "dev") != "prod" else None,
    redoc_url="/redoc" if getattr(_settings, "ENVIRONMENT", "dev") != "prod" else None,
    lifespan=lifespan,
    default_response_class=CustomORJSONResponse, # Enable high-speed JSON rendering globally
)

# Azure Application Insights OpenTelemetry Instrumentation
# try:
#     from azure.monitor.opentelemetry import configure_azure_monitor
#     azure_conn_str = os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING")
#     if azure_conn_str:
#         configure_azure_monitor(connection_string=azure_conn_str)
#         logger.info("✅ Azure Application Insights OpenTelemetry enabled")
#     else:
#         logger.warning("⚠️ APPLICATIONINSIGHTS_CONNECTION_STRING not found, Azure telemetry disabled")
# except ImportError:
#     logger.warning("⚠️ azure-monitor-opentelemetry not installed, skipping Azure telemetry")
# except Exception as e:
#     logger.error(f"❌ Failed to load Azure telemetry: {str(e)}")

app.add_middleware(
    GZipMiddleware,
    minimum_size=1000,
    compresslevel=6
)

# Add CORS middleware for cross-origin requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add performance monitoring middleware
@app.middleware("http")
async def add_performance_headers(request: Request, call_next):
    """Add performance-related headers and track metrics."""
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    process_time_ms = process_time * 1000
    
    # Track latency for benchmarking
    endpoint = f"{request.method} {request.url.path}"
    monitoring.performance.latency_collector.add_latency(endpoint, process_time_ms)
    
    # Add performance headers
    response.headers["X-Process-Time"] = str(process_time)
    response.headers["X-Cache-Status"] = "enabled"
    
    return response


@app.get("/", response_model=dict[str, Any])
async def root() -> dict[str, Any]:
    """
    Root endpoint - provides service information and available endpoints.
    
    Returns:
        dict: Service details and endpoint information
    """
    return {
        "message": "AI OCR & Search Service",
        "version": "0.3",
        "documentation": "/docs",
        "alternative_docs": "/redoc",
        "endpoints": {
            "health": "/health",
            "ocr": {
                "extract": "/ocr/extract (POST)"
            },
            "search": {
                "medicine": "/search/medicine (GET)",
                "provider": "/search/provider (GET)",
                "all": "/search/all (GET)",
                "date_range": "/search/date-range (GET)",
                "autocomplete": "/search/autocomplete (GET)",
                "fuzzy": "/search/fuzzy (GET)",
                "async": "/search/medicine-async (GET)"
            },
            "chat": {
                "chat": "/chat/chat (POST)"
            }
        }
    }


@app.get("/health", response_model=dict[str, Any])
async def health_check() -> dict[str, Any]:
    """
    Comprehensive health check endpoint that verifies service status and external dependencies.
    """
    from app.core.db.elasticsearch import check_es_health
    from app.core.storage.cache import check_redis_health
    from app.services.search.search_indexer import es_service
    
    health_status: Dict[str, Any] = {
        "status": "ok",
        "service": "ai-ocr-search",
        "version": settings.VERSION,
        "timestamp": time.time(),
        "checks": {}
    }
    
    # Check OCR providers
    try:
        ocr_providers = settings.validate_ocr_providers()
        ocr_available = any(p["enabled"] for p in ocr_providers.values())
        health_status["checks"]["ocr_providers"] = {
            "status": "healthy" if ocr_available else "degraded",
            "available": list([k for k, v in ocr_providers.items() if v["enabled"]])
        }
    except Exception as e:
        health_status["checks"]["ocr_providers"] = {
            "status": "error",
            "error": str(e)
        }
    
    # Check extraction providers
    try:
        extraction_providers = settings.validate_extraction_providers()
        extraction_available = any(p["enabled"] for p in extraction_providers.values())
        health_status["checks"]["extraction_providers"] = {
            "status": "healthy" if extraction_available else "degraded",
            "available": list([k for k, v in extraction_providers.items() if v["enabled"]])
        }
    except Exception as e:
        health_status["checks"]["extraction_providers"] = {
            "status": "error",
            "error": str(e)
        }
    
    # Check Elasticsearch
    try:
        if settings.ELASTICSEARCH_ENABLED:
            es_healthy = await es_service.health_check()
            health_status["checks"]["elasticsearch"] = {
                "status": "healthy" if es_healthy else "unhealthy",
                "host": settings.ES_HOST
            }
        else:
            health_status["checks"]["elasticsearch"] = {
                "status": "disabled"
            }
    except Exception as e:
        health_status["checks"]["elasticsearch"] = {
            "status": "error",
            "error": str(e)
        }
    
    # Check Redis
    try:
        if settings.REDIS_ENABLED:
            redis_healthy = await check_redis_health()
            health_status["checks"]["redis"] = {
                "status": "healthy" if redis_healthy else "unhealthy"
            }
        else:
            health_status["checks"]["redis"] = {
                "status": "disabled"
            }
    except Exception as e:
        health_status["checks"]["redis"] = {
            "status": "error",
            "error": str(e)
        }
    
    # Determine overall status
    all_healthy = all(
        check.get("status") in ("healthy", "disabled")
        for check in health_status["checks"].values()
    )
    any_error = any(
        check.get("status") == "error"
        for check in health_status["checks"].values()
    )
    
    if any_error:
        health_status["status"] = "error"
    elif not all_healthy:
        health_status["status"] = "degraded"
    else:
        health_status["status"] = "healthy"
    
    return health_status

@app.get("/debug/env")
async def debug_env() -> dict[str, Any]:
    return {
        "ES_USER": settings.ES_USER,
        "ES_PASS_LENGTH": len(settings.ES_PASS) if settings.ES_PASS else 0,
        "ES_HOST": settings.ES_HOST
    }


from app.core.monitoring.telemetry import SystemTelemetry

@app.get("/performance/metrics")
async def get_performance_metrics():
    """Returns P50/P95/P99 latency benchmarks and system telemetry."""
    return {
        "metrics": latency_collector.get_stats(),
        "system": SystemTelemetry.get_metrics(),
        "timestamp": time.time()
    }


# Include API routers
app.include_router(chat_router, prefix="/chat", tags=["Chat"])
app.include_router(ocr_router, prefix="/ocr", tags=["OCR"])
app.include_router(search_router, prefix="/search")
app.include_router(autocomplete_router, prefix="/autocomplete")

if __name__ == "__main__":
    import uvicorn
    
    # Configure uvicorn with sensible defaults for production
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info",
        access_log=True,
        timeout_keep_alive=30,
        limit_concurrency=100,
    )