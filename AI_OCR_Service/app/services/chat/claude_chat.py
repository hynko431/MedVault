import os
import httpx
import logging
import asyncio
import concurrent.futures
from typing import Optional, Any, Callable, cast
from app.core.config.config import settings
from app.core.monitoring.performance import CircuitBreaker, CircuitBreakerOpen

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

CLAUDE_API_URL = "https://api.anthropic.com/v1/messages"
CLAUDE_MODEL = "claude-3-5-sonnet-20240620"

# Circuit breakers for each chat provider
_anthropic_circuit = CircuitBreaker(failure_threshold=3, recovery_timeout=30.0)
_openrouter_circuit = CircuitBreaker(failure_threshold=3, recovery_timeout=30.0)
_groq_circuit = CircuitBreaker(failure_threshold=3, recovery_timeout=30.0)

# HTTP client with connection pooling
_http_client: Optional[httpx.AsyncClient] = None

def get_http_client() -> httpx.AsyncClient:
    """Get or create async HTTP client with connection pooling."""
    global _http_client
    if _http_client is None:
        _http_client = httpx.AsyncClient(
            timeout=httpx.Timeout(30.0, connect=10.0),
            limits=httpx.Limits(max_connections=100, max_keepalive_connections=20)
        )
    return _http_client

async def close_http_client() -> None:
    """Close the HTTP client connection."""
    global _http_client
    if _http_client is not None:
        await _http_client.aclose()
        _http_client = None

def get_medicine_chat_prompt(question: str, context: dict | None = None) -> str:
    """Generate the prompt for medicine chat"""
    return f"""
        You are a medical information assistant.
        You DO NOT diagnose.
        You DO NOT give emergency advice.

        Rules:
        - Explain medicines in plain English
        - Mention common uses, side effects, precautions
        - Always include a disclaimer
        - If unsure, say you are unsure

        Question:
        {question}
        """

async def try_anthropic(prompt: str) -> str:
    """Try Anthropic Claude API asynchronously with circuit breaker"""
    if not await _anthropic_circuit.can_execute():
        raise CircuitBreakerOpen("Anthropic circuit breaker is open")
    
    if not settings.ANTHROPIC_API_KEY:
        raise RuntimeError("ANTHROPIC_API_KEY not set")
    
    logger.info("Attempting chat with Anthropic...")
    
    headers = {
        "x-api-key": settings.ANTHROPIC_API_KEY,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json"
    }
    
    payload = {
        "model": CLAUDE_MODEL,
        "max_tokens": 300,
        "messages": [
            {"role": "user", "content": prompt}
        ]
    }
    
    try:
        client = get_http_client()
        # Apply timeout (10 seconds for chat)
        response = await asyncio.wait_for(
            client.post(CLAUDE_API_URL, headers=headers, json=payload),
            timeout=10.0
        )
        
        if response.status_code != 200:
            logger.error(f"Anthropic API error: {response.status_code} - {response.text}")
        
        response.raise_for_status()
        
        # Validate JSON structure before parsing
        json_str = response.text
        # Check for basic JSON object/array structure
        if not json_str or not (json_str.strip().startswith('{') or json_str.strip().startswith('[')):
            logger.error(f"Response does not appear to be valid JSON: {json_str[:200] if json_str else 'EMPTY'}")
            raise ValueError("Response does not contain valid JSON structure")
        
        result = response.json()
        if isinstance(result, dict) and "content" in result:
            content_list = result["content"]
            if isinstance(content_list, list) and len(content_list) > 0:
                content_item = content_list[0]
                if isinstance(content_item, dict) and "text" in content_item:
                    text_val = content_item["text"]
                    await _anthropic_circuit.record_success()
                    return str(text_val)  # Ensure string return
        raise ValueError("Invalid response format from Anthropic API")
    except Exception as e:
        await _anthropic_circuit.record_failure()
        raise

async def try_openrouter(prompt: str) -> str:
    """Try OpenRouter API as fallback asynchronously with circuit breaker"""
    if not await _openrouter_circuit.can_execute():
        raise CircuitBreakerOpen("OpenRouter circuit breaker is open")
    
    if not settings.OPENROUTER_API_KEY:
        raise RuntimeError("OPENROUTER_API_KEY not set")
    
    logger.info("Attempting chat with OpenRouter...")
    
    headers = {
        "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/hynko431/MedVault",
        "X-Title": "MedVault AI OCR"
    }
    
    payload = {
        "model": settings.OPENROUTER_MODEL,
        "messages": [{"role": "user", "content": prompt}]
    }
    
    try:
        client = get_http_client()
        # Apply timeout (10 seconds for chat)
        response = await asyncio.wait_for(
            client.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload),
            timeout=10.0
        )
        
        if response.status_code != 200:
            logger.error(f"OpenRouter API error: {response.status_code} - {response.text}")
        
        response.raise_for_status()
        result = response.json()
        if isinstance(result, dict) and "choices" in result:
            choices_list = result["choices"]
            if isinstance(choices_list, list) and len(choices_list) > 0:
                choice_item = choices_list[0]
                if isinstance(choice_item, dict) and "message" in choice_item:
                    message_item = choice_item["message"]
                    if isinstance(message_item, dict) and "content" in message_item:
                        text_val = message_item["content"]
                        await _openrouter_circuit.record_success()
                        return str(text_val)
        raise ValueError("Invalid response format from OpenRouter API")
    except Exception as e:
        await _openrouter_circuit.record_failure()
        raise

async def try_groq(prompt: str) -> str:
    """Try Groq API as final fallback asynchronously with circuit breaker"""
    if not await _groq_circuit.can_execute():
        raise CircuitBreakerOpen("Groq circuit breaker is open")
    
    if not settings.GROQ_API_KEY:
        raise RuntimeError("GROQ_API_KEY not set")
    
    logger.info("Attempting chat with Groq...")
    
    headers = {
        "Authorization": f"Bearer {settings.GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": settings.GROQ_MODEL,
        "messages": [{"role": "user", "content": prompt}]
    }
    
    try:
        client = get_http_client()
        # Apply timeout (10 seconds for chat)
        response = await asyncio.wait_for(
            client.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload),
            timeout=10.0
        )
        
        if response.status_code != 200:
            logger.error(f"Groq API error: {response.status_code} - {response.text}")
        
        response.raise_for_status()
        result = response.json()
        if isinstance(result, dict) and "choices" in result:
            choices_list = result["choices"]
            if isinstance(choices_list, list) and len(choices_list) > 0:
                choice_item = choices_list[0]
                if isinstance(choice_item, dict) and "message" in choice_item:
                    message_item = choice_item["message"]
                    if isinstance(message_item, dict) and "content" in message_item:
                        text_val = message_item["content"]
                        await _groq_circuit.record_success()
                        return str(text_val)
        raise ValueError("Invalid response format from Groq API")
    except Exception as e:
        await _groq_circuit.record_failure()
        raise

def _log_provider_error(provider_name: str, error: Exception, errors: list) -> None:
    """
    Log an error from a provider and add it to the errors list.
    
    Args:
        provider_name: Name of the provider that failed
        error: The exception that occurred
        errors: List to append the error message to
    """
    err = f"{provider_name}: {str(error)}"
    logger.warning(err)
    errors.append(err)


async def medicine_chat(question: str, context: dict | None = None) -> str:
    """
    Chat with AI about medicine-related questions with fallback mechanism.
    
    Fallback chain: Anthropic → OpenRouter → Groq
    
    Args:
        question: User's question about medicines
        context: Optional context dictionary (for future enhancements)
    
    Returns:
        AI-generated response
    
    Raises:
        RuntimeError: If all AI providers fail
    """
    prompt = get_medicine_chat_prompt(question, context)
    errors: list[str] = []

    # 1. Try Anthropic (Primary)
    try:
        return await try_anthropic(prompt)
    except Exception as e:
        _log_provider_error("Anthropic", e, errors)
    
    # 2. Try OpenRouter (Fallback 1)
    try:
        return await try_openrouter(prompt)
    except Exception as e:
        _log_provider_error("OpenRouter", e, errors)
    
    # 3. Try Groq (Fallback 2)
    try:
        return await try_groq(prompt)
    except Exception as e:
        _log_provider_error("Groq", e, errors)
    
    # All providers failed
    error_message = f"All AI providers failed. Errors: {'; '.join(errors)}"
    logger.error(error_message)
    return f"Error: {error_message}"


# Helper for synchronous wrapper
def _run_coro(coro: Any) -> Any:
    """Wrapper to run a coroutine in a synchronous context."""
    return asyncio.run(coro)


# Backward compatibility: synchronous wrapper
def medicine_chat_sync(question: str, context: dict | None = None) -> str:
    """
    Synchronous wrapper for medicine_chat.
    
    Note: This should be used only when async context is not available.
    Prefer using medicine_chat() directly in async contexts.
    """
    try:
        loop = asyncio.get_running_loop()
        # We're already in an async context, use run_in_executor
        with concurrent.futures.ThreadPoolExecutor() as executor:
            # Use top-level wrapper to help Pyre2 infer types correctly
            fn = cast(Callable[..., Any], _run_coro)
            future = executor.submit(fn, medicine_chat(question, context))
            result = future.result()
            return str(result) if result is not None else ""
    except RuntimeError:
        # No running loop, we can use asyncio.run
        return asyncio.run(medicine_chat(question, context))
    return ""
