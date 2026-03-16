import asyncio
import logging
from typing import Optional, cast, Iterable, List
from functools import wraps

from app.core import get_settings, logger, monitoring
settings = get_settings()

logger = logger.get_logger("vision_ocr")

# Circuit breakers for each OCR provider
_gemini_circuit = monitoring.performance.CircuitBreaker(failure_threshold=3, recovery_timeout=30.0)
_google_vision_circuit = monitoring.performance.CircuitBreaker(failure_threshold=3, recovery_timeout=30.0)
_hf_paddle_circuit = monitoring.performance.CircuitBreaker(failure_threshold=3, recovery_timeout=30.0)
_paddle_circuit = monitoring.performance.CircuitBreaker(failure_threshold=3, recovery_timeout=30.0)

# Lazy-loaded OCR services
_gemini_ocr = None
_google_vision_ocr = None
_paddle_ocr_service = None
GeminiOCRError = None
GoogleOCRError = None
PaddleOCRError = None
HFOCRError = None

def _get_gemini_ocr():
    """Lazy load Gemini OCR service"""
    global _gemini_ocr, GeminiOCRError
    if _gemini_ocr is None:
        from app.services.ocr.gemini_ocr import extract_text_with_gemini, GeminiOCRError as _GeminiError
        _gemini_ocr = extract_text_with_gemini
        GeminiOCRError = _GeminiError
    return _gemini_ocr

def _get_google_vision_ocr():
    """Lazy load Google Vision OCR service"""
    global _google_vision_ocr, GoogleOCRError
    if _google_vision_ocr is None:
        from app.services.ocr.google_vision_ocr import extract_text_from_image, OCRError
        _google_vision_ocr = extract_text_from_image
        GoogleOCRError = OCRError
    return _google_vision_ocr

def _get_paddle_ocr_service():
    """Lazy load PaddleOCR service"""
    global _paddle_ocr_service, PaddleOCRError
    if _paddle_ocr_service is None:
        from app.services.ocr.paddle_ocr import extract_text_with_paddle, PaddleOCRError as _PaddleOCRError
        _paddle_ocr_service = extract_text_with_paddle
        PaddleOCRError = _PaddleOCRError
    return _paddle_ocr_service

class UnifiedOCRError(Exception):
    """Raised when all OCR providers fail"""
    pass

def retry_with_backoff(max_retries: int = 2, backoff_factor: float = 2.0, timeout: float = 30.0):
    """
    Decorator for retrying failed async API calls with exponential backoff and timeout.
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception: Optional[Exception] = None
            for attempt in range(max_retries):
                try:
                    # Apply timeout to each attempt
                    return await asyncio.wait_for(
                        func(*args, **kwargs),
                        timeout=timeout
                    )
                except asyncio.TimeoutError:
                    last_exception = TimeoutError(f"{func.__name__} timed out after {timeout}s")
                    logger.warning(f"{func.__name__} attempt {attempt + 1}/{max_retries} timed out")
                except Exception as e:
                    error_str = str(e).lower()
                    if any(config_error in error_str for config_error in 
                           ["not set", "not configured", "not found", "credentials", "api_key"]):
                        logger.error(f"Configuration error in {func.__name__}: {str(e)}. Failing fast.")
                        raise
                    
                    last_exception = e
                    if attempt < max_retries - 1:
                        wait_time = backoff_factor ** attempt
                        logger.warning(
                            f"{func.__name__} attempt {attempt + 1}/{max_retries} failed. "
                            f"Retrying in {wait_time}s... Error: {str(e)}"
                        )
                        await asyncio.sleep(wait_time)
                    else:
                        logger.error(
                            f"{func.__name__} failed after {max_retries} attempts. "
                            f"Final error: {str(e)}"
                        )
            if last_exception is None:
                raise RuntimeError(f"{func.__name__} completed without success or exception")
            raise last_exception
        return wrapper
    return decorator

async def _try_gemini(image_bytes: bytes) -> str:
    """Primary OCR provider: Google Gemini with circuit breaker."""
    if not await _gemini_circuit.can_execute():
        raise monitoring.performance.CircuitBreakerOpen("Gemini circuit breaker is open")
    
    logger.info(f"🤖 Attempting OCR with {settings.GEMINI_MODEL} (1st Priority)...")
    try:
        gemini_func = _get_gemini_ocr()
        # Apply timeout for Gemini (30 seconds)
        text = await asyncio.wait_for(gemini_func(image_bytes), timeout=30.0)
        await _gemini_circuit.record_success()
        logger.info(f"✅ Gemini succeeded. Extracted {len(text) if text else 0} characters.")
        return str(text)
    except Exception as e:
        await _gemini_circuit.record_failure()
        logger.warning(f"❌ Gemini failed: {str(e)}")
        raise
async def _try_google_vision(image_bytes: bytes) -> str:
    """Secondary OCR provider: Google Cloud Vision API with circuit breaker."""
    if not await _google_vision_circuit.can_execute():
        raise monitoring.performance.CircuitBreakerOpen("Google Vision circuit breaker is open")
    
    logger.info("🔍 Attempting OCR with Google Cloud Vision (2nd Priority)...")
    try:
        vision_func = _get_google_vision_ocr()
        # Apply timeout for Google Vision (20 seconds)
        text = await asyncio.wait_for(vision_func(image_bytes), timeout=20.0)
        await _google_vision_circuit.record_success()
        logger.info(f"✅ Google Vision succeeded. Extracted {len(text) if text else 0} characters.")
        return str(text)
    except Exception as e:
        await _google_vision_circuit.record_failure()
        logger.warning(f"❌ Google Vision failed: {str(e)}")
        raise

async def _try_hf_paddle(image_bytes: bytes) -> str:
    """Tertiary OCR provider: Hugging Face PaddleOCR Endpoint with circuit breaker."""
    if not await _hf_paddle_circuit.can_execute():
        raise monitoring.performance.CircuitBreakerOpen("HF PaddleOCR circuit breaker is open")
    
    if not settings.HF_PADDLE_OCR_ENDPOINT_URL:
        raise ValueError("HF PaddleOCR Endpoint URL not set")
    
    logger.info("☁️ Attempting OCR with HF PaddleOCR (3rd Priority)...")
    try:
        from app.services.ocr.hf_paddle_ocr import extract_text_with_hf_paddle
        # Apply timeout for HF PaddleOCR (25 seconds)
        text = await asyncio.wait_for(extract_text_with_hf_paddle(image_bytes), timeout=25.0)
        # text is guaranteed to be a non-empty string if no exception was raised
        await _hf_paddle_circuit.record_success()
        logger.info(f"✅ HF PaddleOCR succeeded. Extracted {len(text) if text else 0} characters.")
        return str(text)
    except Exception as e:
        await _hf_paddle_circuit.record_failure()
        logger.warning(f"❌ HF PaddleOCR failed: {str(e)}")
        raise

async def _try_paddle(image_bytes: bytes) -> str:
    """Fallback OCR provider: Local PaddleOCR with circuit breaker."""
    if not await _paddle_circuit.can_execute():
        raise monitoring.performance.CircuitBreakerOpen("Local PaddleOCR circuit breaker is open")
    
    logger.info("📚 Attempting OCR with Local PaddleOCR (Fallback)...")
    try:
        paddle_func = _get_paddle_ocr_service()
        # Apply timeout for Local PaddleOCR (60 seconds - can be slower)
        text = await asyncio.wait_for(paddle_func(image_bytes), timeout=60.0)
        await _paddle_circuit.record_success()
        logger.info(f"✅ Local PaddleOCR succeeded. Extracted {len(text) if text else 0} characters.")
        return str(text)
    except Exception as e:
        await _paddle_circuit.record_failure()
        logger.warning(f"❌ Local PaddleOCR failed: {str(e)}")
        raise

async def _race_providers(image_bytes: bytes, providers: list, timeout: float = 15.0) -> str:
    """
    Race multiple OCR providers with proper cleanup and resource management.
    """
    if not providers:
        raise UnifiedOCRError("No providers configured for racing")
    
    # Create tasks for all providers
    tasks: List[asyncio.Task[str]] = [asyncio.create_task(provider_func(image_bytes)) for provider_func in providers]
    pending_tasks: set[asyncio.Task[str]] = set(asyncio.ensure_future(t) for t in tasks)
    errors: List[str] = []
    
    async def _cleanup_pending(cancel_set: set[asyncio.Task[str]], cleanup_timeout: float = 5.0) -> None:
        """Helper to properly cancel and cleanup pending tasks."""
        if not cancel_set:
            return
        
        for t in cancel_set:
            if not t.done():
                t.cancel()
        
        try:
            # Use list conversion for gather
            await asyncio.wait_for(
                asyncio.gather(*list(cancel_set), return_exceptions=True),
                timeout=cleanup_timeout
            )
        except asyncio.TimeoutError:
            logger.warning(f"Some tasks didn't cancel within {cleanup_timeout}s")
    
    try:
        while pending_tasks:
            # Wait for the first completed task
            # Use list(pending_tasks) for better compatibility with some type checkers
            res = await asyncio.wait(
                list(pending_tasks),
                return_when=asyncio.FIRST_COMPLETED,
                timeout=timeout
            )
            done_tasks, pending_tasks = cast(tuple[set[asyncio.Task[str]], set[asyncio.Task[str]]], res)
            
            # Process completed tasks
            for task in done_tasks:
                try:
                    result: str = task.result()
                    # Success! Cleanup remaining tasks
                    if pending_tasks:
                        await _cleanup_pending(cast(set[asyncio.Task[str]], pending_tasks))
                    return result
                except Exception as e:
                    error_msg: str = str(e)
                    if "circuit breaker is open" not in error_msg.lower():
                        errors.append(error_msg)
                    logger.debug(f"Provider failed in race: {error_msg}")
            
            if not pending_tasks:
                break
        
        error_details = " | ".join(errors) if errors else "All providers failed"
        raise UnifiedOCRError(f"All providers failed: {error_details}")
        
    except asyncio.TimeoutError:
        await _cleanup_pending(pending_tasks)
        raise UnifiedOCRError(f"All providers timed out after {timeout}s")
    except Exception:
        await _cleanup_pending(pending_tasks)
        raise


async def extract_text_with_fallback(image_bytes: bytes) -> str:
    """
    Extract text from image using optimized pipeline:
    - Parallel mode: Try Gemini + Google Vision simultaneously (race)
    - Sequential mode: Fallback to HF PaddleOCR and Local PaddleOCR
    
    Configuration:
    - Set OCR_PARALLEL_ENABLED=true to enable racing (default: true)
    - Set OCR_PARALLEL_TIMEOUT=15 for race timeout (default: 15s)
    """
    if not isinstance(image_bytes, bytes):
        raise TypeError(f"Expected bytes, got {type(image_bytes).__name__}")
    
    if len(image_bytes) == 0:
        raise ValueError("Image bytes cannot be empty")
    
    # Check if parallel mode is enabled
    parallel_enabled = getattr(settings, 'OCR_PARALLEL_ENABLED', True)
    parallel_timeout = getattr(settings, 'OCR_PARALLEL_TIMEOUT', 15.0)
    
    errors = []
    
    if parallel_enabled:
        # PHASE 4 OPTIMIZATION: Race Gemini + Google Vision
        logger.info("🚀 Starting parallel OCR execution (race mode)...")
        
        # Primary tier: Race Gemini and Google Vision
        primary_providers = []
        
        # Check if Gemini is available (circuit breaker + API key)
        if await _gemini_circuit.can_execute() and settings.GEMINI_API_KEY:
            primary_providers.append(_try_gemini)
        
        # Check if Google Vision is available
        if await _google_vision_circuit.can_execute() and settings.GOOGLE_APPLICATION_CREDENTIALS:
            primary_providers.append(_try_google_vision)
        
        if primary_providers:
            try:
                result = await _race_providers(
                    image_bytes, 
                    primary_providers, 
                    timeout=parallel_timeout
                )
                logger.info(f"✅ Parallel OCR succeeded with fastest provider")
                return result
            except UnifiedOCRError as e:
                logger.warning(f"⚠️ All primary providers failed in race: {e}")
                errors.append(f"Race: {str(e)}")
        else:
            logger.warning("⚠️ No primary providers available for racing")
    
    # Sequential fallback tier: HF PaddleOCR
    if settings.HF_PADDLE_OCR_ENDPOINT_URL and await _hf_paddle_circuit.can_execute():
        try:
            logger.info("☁️ Trying HF PaddleOCR (sequential)...")
            return await _try_hf_paddle(image_bytes)
        except Exception as e:
            errors.append(f"HF PaddleOCR: {str(e)}")
    
    # Final fallback tier: Local PaddleOCR
    if await _paddle_circuit.can_execute():
        try:
            logger.info("📚 Trying Local PaddleOCR (final fallback)...")
            return await _try_paddle(image_bytes)
        except Exception as e:
            errors.append(f"Local PaddleOCR: {str(e)}")
    
    # All failed
    error_details = " | ".join(errors)
    logger.error(f"🚨 All OCR providers failed: {error_details}")
    raise UnifiedOCRError(f"Unable to extract text. All providers failed:\n{error_details}")

async def extract_text_from_image(image_bytes: bytes) -> str:
    """Legacy interface."""
    return await extract_text_with_fallback(image_bytes)
