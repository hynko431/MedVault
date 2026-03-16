"""
Unified Elasticsearch client management.
Provides singleton client with proper lifecycle management.
"""

from typing import Optional, Any, TYPE_CHECKING

# Always-available fallback type so Pyre2 never sees Unknown
try:
    from elasticsearch import AsyncElasticsearch, ElasticsearchException
except ImportError:  # pragma: no cover
    AsyncElasticsearch = None  # type: ignore[assignment, misc]
    ElasticsearchException = Exception  # type: ignore[assignment, misc]

from app.core.config.config import settings
from app.core.logging.logger import get_logger

logger = get_logger(__name__)


class ElasticsearchClientManager:
    """Singleton manager for Elasticsearch clients."""

    _instance: Optional["ElasticsearchClientManager"] = None
    _sync_client: Optional[Any] = None
    _async_client: Optional[Any] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @property
    def is_enabled(self) -> bool:
        """Check if Elasticsearch is enabled."""
        return settings.ELASTICSEARCH_ENABLED

    def get_sync_client(self) -> Optional[Any]:
        """Get or create synchronous Elasticsearch client."""
        if not self.is_enabled:
            return None

        if self._sync_client is None:
            if settings.ELASTICSEARCH_HOST and settings.ELASTICSEARCH_HOST != "http://127.0.0.1:9200":
                host = settings.ELASTICSEARCH_HOST
            else:
                host = settings.ES_HOST

            client_config: dict = {
                "hosts": [host],
                "verify_certs": settings.ES_VERIFY_CERTS if hasattr(settings, "ES_VERIFY_CERTS") else False,
            }
            
            if AsyncElasticsearch is not None:
                self._sync_client = AsyncElasticsearch(**client_config) # type: ignore[misc]

        return self._sync_client

    def get_async_client(self) -> Optional[Any]:
        """Get or create asynchronous Elasticsearch client."""
        if not self.is_enabled:
            return None

        if self._async_client is None:
            client_config: dict = {
                "hosts": [settings.ES_HOST],
                "verify_certs": settings.ES_VERIFY_CERTS,
                "request_timeout": settings.ES_TIMEOUT,
                "max_retries": settings.ES_MAX_RETRIES,
                "retry_on_timeout": True,
                "headers": {"Accept": "application/vnd.elasticsearch+json; compatible-with=8"},
                "connections_per_node": 25,
                "http_compress": True,
                "sniff_on_start": False,
                "sniff_on_connection_fail": False,
            }

            if settings.ES_API_KEY:
                api_key_parts = settings.ES_API_KEY.split(".")
                if len(api_key_parts) == 2:
                    client_config["api_key"] = (api_key_parts[0], api_key_parts[1])
                else:
                    client_config["api_key"] = settings.ES_API_KEY
                logger.info(f"Created async ES client with API key for {settings.ES_HOST}")
            else:
                client_config["basic_auth"] = (settings.ES_USER, settings.ES_PASS)
                logger.info(f"Created async ES client with basic auth for {settings.ES_HOST}")

            if AsyncElasticsearch is not None:
                self._async_client = AsyncElasticsearch(**client_config) # type: ignore[misc]

        return self._async_client

    async def close(self) -> None:
        """Close all client connections."""
        if self._async_client is not None:
            await self._async_client.close()
            self._async_client = None
            logger.info("Closed async ES client")

        if self._sync_client is not None:
            sync_cl = self._sync_client
            if hasattr(sync_cl, 'close'):
                sync_cl.close()
            self._sync_client = None
            logger.info("Closed sync ES client")


# Global singleton
es_client_manager = ElasticsearchClientManager()