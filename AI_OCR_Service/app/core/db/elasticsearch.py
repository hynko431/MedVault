"""
Elasticsearch client compatibility layer.
Provides the interface expected by main.py by wrapping es_client_manager.
"""

from typing import Optional, Any, AsyncGenerator
from app.core.db.es_client import es_client_manager
from app.core.logging.logger import get_logger

logger = get_logger(__name__)


def get_es_client() -> Optional[Any]:
    """
    Get or create the global AsyncElasticsearch client.
    
    Returns:
        AsyncElasticsearch client instance or None if ES is disabled
    """
    return es_client_manager.get_async_client()


async def close_es_client() -> None:
    """Close the global Elasticsearch client connection."""
    await es_client_manager.close()


async def get_es() -> AsyncGenerator[Any, None]:
    """
    FastAPI dependency that provides request-scoped Elasticsearch client.
    
    Usage:
        @app.get("/search")
        async def search(q: str, es: AsyncElasticsearch = Depends(get_es)):
            result = await es.search(index="prescriptions", body={"query": {"match_all": {}}})
            return result
    
    Yields:
        AsyncElasticsearch client instance
    """
    client = get_es_client()
    try:
        yield client
    finally:
        # Connection is managed globally, so we don't close it per-request
        pass


async def check_es_health() -> bool:
    """
    Check if Elasticsearch is available and healthy.
    
    Returns:
        True if ES is healthy, False otherwise
    """
    import aiohttp
    
    try:
        from app.core.config.config import settings
        
        # Prepare headers and auth based on configuration
        headers = {"Accept": "application/json"}
        
        if settings.ES_API_KEY:
            headers["Authorization"] = f"ApiKey {settings.ES_API_KEY}"
            auth = None
            logger.debug("Using API key authentication for health check")
        else:
            auth = aiohttp.BasicAuth(settings.ES_USER, settings.ES_PASS)
            logger.debug("Using basic authentication for health check")
        
        # Use direct HTTP check instead of client methods to avoid library issues
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{settings.ES_HOST}/_cluster/health",
                headers=headers,
                auth=auth,
                timeout=aiohttp.ClientTimeout(total=5),
                ssl=False
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    cluster_status = data.get('status', 'unknown')
                    logger.debug(f"Elasticsearch cluster status: {cluster_status}")
                    # Consider green or yellow as healthy
                    return cluster_status in ('green', 'yellow')
                elif response.status == 401:
                    logger.warning("Elasticsearch authentication failed (401). Check ES_API_KEY or ES_USER/ES_PASS.")
                    return False
                else:
                    logger.warning(f"Elasticsearch health check returned status: {response.status}")
                    return False
                
    except aiohttp.ClientConnectorError as e:
        logger.warning(f"Cannot connect to Elasticsearch: {e}")
        return False
    except Exception as e:
        logger.warning(f"Elasticsearch health check failed: {e}")
        return False