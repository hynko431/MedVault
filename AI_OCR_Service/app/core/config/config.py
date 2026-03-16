from dotenv import load_dotenv
load_dotenv(override=True)  # Must run before Settings() to ensure .env takes priority over cached os.environ

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from typing import Optional, Any

class Settings(BaseSettings):
    """Application settings loaded automatically from .env file."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )
    
    PROJECT_NAME: str = "AI OCR & Search Service"
    VERSION: str = "0.3"
    
    # Google Cloud Vision
    GOOGLE_APPLICATION_CREDENTIALS: Optional[str] = None
    
    # Gemini (OCR Priority 1) - Using Interactions API with latest models
    GEMINI_API_KEY: Optional[str] = None
    GEMINI_MODEL: str = "gemini-3-flash-preview"
    
    # Anthropic (Primary OCR/Extraction)
    ANTHROPIC_API_KEY: Optional[str] = None
    ANTHROPIC_MODEL: str = "claude-3-5-sonnet-20240620"
    
    # OpenAI (Fallback/Embedding)
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_MODEL: str = "text-embedding-3-small"
    
    # OpenRouter (Fallback 1)
    OPENROUTER_API_KEY: Optional[str] = None
    OPENROUTER_MODEL: str = "google/gemma-3-27b-it:free"
    
    # Groq (Fallback 2)
    GROQ_API_KEY: Optional[str] = None
    GROQ_MODEL: str = "openai/gpt-oss-120b"
    
    # Hugging Face Inference Endpoints
    HF_PADDLE_OCR_ENDPOINT_URL: Optional[str] = None
    HF_API_KEY: Optional[str] = None
    
    # Elasticsearch Configuration
    ELASTICSEARCH_ENABLED: bool = False
    # ES_HOST is the canonical setting; ELASTICSEARCH_HOST is deprecated but kept for backward compatibility
    ES_HOST: str = "http://127.0.0.1:9200"
    ELASTICSEARCH_HOST: str = Field(
        default="http://127.0.0.1:9200",
        deprecated="Use ES_HOST instead. This field is kept for backward compatibility.",
    )
    ES_USER: str = "elastic"
    ES_PASS: str = "changeme123"
    ES_API_KEY: Optional[str] = None  # Optional: Use API key instead of basic_auth
    ES_INDEX: str = "prescriptions_current"
    ES_WRITE_INDEX: str = "prescriptions-prod-write"
    ES_PROD_INDEX: str = "prescriptions-prod-write"
    ES_INDEX_ALIAS: str = "prescriptions_current"
    ES_REPLICAS: int = 0  # 0 for single-node local, 1 for production HA
    ES_VERIFY_CERTS: bool = False
    ES_TIMEOUT: int = 5
    ES_MAX_RETRIES: int = 3
    
    # Hybrid Search Configuration
    ES_HYBRID_ALPHA: float = 0.8  # Lexical weight
    ES_HYBRID_BETA: float = 0.2   # Semantic weight
    ES_VECTOR_DIMS: int = 768     # Dimensions for Jina v5 / GTE
    
    # Embedding Configuration
    JINA_API_KEY: Optional[str] = None
    EMBEDDING_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"
    EMBEDDING_FALLBACK_ENABLED: bool = True
    
    # Search Strategy Configuration (Feature Flag)
    # Options: "prefix" (fast prefix-only), "prefix_fuzzy" (prefix + fuzzy combined)
    SEARCH_STRATEGY: str = "prefix_fuzzy"
    
    # Redis Configuration (for caching)
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_ENABLED: bool = False  # Set to True to enable Redis caching
    
    # LangSmith Configuration
    LANGCHAIN_TRACING_V2: Optional[str] = None
    LANGSMITH_API_KEY: Optional[str] = None
    LANGCHAIN_PROJECT: Optional[str] = None
    
    # Performance Configuration
    CACHE_TTL_SECONDS: int = 300  # Default cache TTL (5 minutes)
    CACHE_SYNC_TIMEOUT: int = 5  # Timeout for sync cache operations (seconds)
    ENABLE_COMPRESSION: bool = True  # Enable GZip compression
    COMPRESSION_MINIMUM_SIZE: int = 1000  # Minimum response size to compress (bytes)
    COMPRESSION_LEVEL: int = 6  # GZip compression level (1-9)
    
    # OCR Provider Timeouts
    GEMINI_TIMEOUT: float = 30.0  # Timeout for Gemini OCR
    GOOGLE_VISION_TIMEOUT: float = 20.0  # Timeout for Google Vision OCR
    HF_PADDLE_TIMEOUT: float = 25.0  # Timeout for HF PaddleOCR
    LOCAL_PADDLE_TIMEOUT: float = 60.0  # Timeout for local PaddleOCR
    
    # AI Extraction Timeouts
    EXTRACTION_TIMEOUT: int = 10  # Timeout for AI extraction
    EXTRACTION_MAX_RETRIES: int = 2  # Max retries for AI extraction
    
    # OCR Parallel Execution Configuration (Phase 4)
    OCR_PARALLEL_ENABLED: bool = True  # Enable parallel OCR execution (race mode)
    OCR_PARALLEL_TIMEOUT: float = 15.0  # Timeout for parallel OCR race (seconds)
    OCR_MAX_CONCURRENT_REQUESTS: int = 10  # Max concurrent OCR requests
    OCR_REQUEST_QUEUE_SIZE: int = 100  # OCR request queue size
    
    # Rate Limiting Configuration
    RATE_LIMIT_OCR_RPM: int = 10  # OCR requests per minute
    RATE_LIMIT_OCR_BURST: int = 3  # OCR burst size
    RATE_LIMIT_CHAT_RPM: int = 30  # Chat requests per minute
    RATE_LIMIT_CHAT_BURST: int = 10  # Chat burst size
    RATE_LIMIT_SEARCH_RPM: int = 100  # Search requests per minute
    RATE_LIMIT_SEARCH_BURST: int = 20  # Search burst size

    def get_masked_key(self, key_name: str) -> str:
        """Mask sensitive key values for logging."""
        val = getattr(self, key_name, None)
        if val:
            return "***" if len(val) <= 8 else f"{val[:4]}...{val[-4:]}"
        else:
            return "NOT SET"

    def validate_required_settings(self, required_keys: list[str] | None = None) -> dict[str, bool]:
        """
        Validate that required environment variables are set.
        
        Args:
            required_keys: List of setting keys to validate. If None, validates 
                          critical API keys for core functionality.
        
        Returns:
            Dictionary mapping key names to validation status (True if valid, False if missing)
        """
        if required_keys is None:
            # Default critical keys for basic operation
            required_keys = ["GEMINI_API_KEY"]
        
        results = {}
        for key in required_keys:
            value = getattr(self, key, None)
            is_valid = value is not None and str(value).strip() != ""
            results[key] = is_valid
        
        return results
    
    def validate_ocr_providers(self) -> dict[str, dict[str, Any]]:
        """
        Validate OCR provider configurations.
        
        Returns:
            Dictionary with provider names and their validation status
        """
        providers = {
            "gemini": {
                "enabled": bool(self.GEMINI_API_KEY),
                "key_configured": bool(self.GEMINI_API_KEY),
                "model": self.GEMINI_MODEL,
            },
            "google_vision": {
                "enabled": bool(self.GOOGLE_APPLICATION_CREDENTIALS),
                "key_configured": bool(self.GOOGLE_APPLICATION_CREDENTIALS),
            },
            "hf_paddle_ocr": {
                "enabled": bool(self.HF_PADDLE_OCR_ENDPOINT_URL and self.HF_API_KEY),
                "key_configured": bool(self.HF_API_KEY),
            },
            "paddle_ocr": {
                "enabled": True,  # PaddleOCR doesn't require API keys
                "key_configured": True,
            }
        }
        return providers
    
    def validate_extraction_providers(self) -> dict[str, dict[str, Any]]:
        """
        Validate AI extraction provider configurations.
        
        Returns:
            Dictionary with provider names and their validation status
        """
        providers = {
            "anthropic": {
                "enabled": bool(self.ANTHROPIC_API_KEY),
                "key_configured": bool(self.ANTHROPIC_API_KEY),
                "model": self.ANTHROPIC_MODEL,
            },
            "openrouter": {
                "enabled": bool(self.OPENROUTER_API_KEY),
                "key_configured": bool(self.OPENROUTER_API_KEY),
                "model": self.OPENROUTER_MODEL,
            },
            "groq": {
                "enabled": bool(self.GROQ_API_KEY),
                "key_configured": bool(self.GROQ_API_KEY),
                "model": self.GROQ_MODEL,
            }
        }
        return providers
    
    def get_validation_report(self) -> dict[str, Any]:
        """
        Generate a comprehensive validation report of all configurations.
        
        Returns:
            Dictionary with validation status for all service categories
        """
        ocr_providers = self.validate_ocr_providers()
        extraction_providers = self.validate_extraction_providers()
        
        # Check if at least one OCR provider is available
        ocr_available = any(p["enabled"] for p in ocr_providers.values())
        
        # Check if at least one extraction provider is available
        extraction_available = any(p["enabled"] for p in extraction_providers.values())
        
        return {
            "ocr_providers": {
                "providers": ocr_providers,
                "at_least_one_available": ocr_available,
                "status": "ok" if ocr_available else "warning"
            },
            "extraction_providers": {
                "providers": extraction_providers,
                "at_least_one_available": extraction_available,
                "status": "ok" if extraction_available else "warning"
            },
            "elasticsearch": {
                "enabled": self.ELASTICSEARCH_ENABLED,
                "host": self.ES_HOST,
                "status": "enabled" if self.ELASTICSEARCH_ENABLED else "disabled"
            },
            "redis": {
                "enabled": self.REDIS_ENABLED,
                "url_configured": bool(getattr(self, 'REDIS_URL', None)),
                "status": "enabled" if self.REDIS_ENABLED else "disabled"
            },
            "overall_status": "ok" if (ocr_available and extraction_available) else "degraded"
        }


# Create singleton settings instance
settings = Settings()