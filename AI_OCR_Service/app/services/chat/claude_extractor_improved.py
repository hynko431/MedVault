"""
Improved version of claude_extractor.py with refactoring suggestions.

Key Improvements:
1. Eliminated code duplication in retry_with_backoff decorator
2. Fixed unsafe response attribute checking
3. Extracted common API call logic to reduce duplication
4. Added proper constants for magic numbers
5. Improved type hints throughout
6. Better error messages and logging
7. Removed module-level logging configuration
8. Enhanced JSON parsing with better error handling
9. Created helper functions for cleaner code
10. Added dataclass for API configuration
"""

import json
import logging
import time
from dataclasses import dataclass
from functools import wraps
from typing import Dict, Callable, Optional, Any
from pydantic import ValidationError
import requests

from app.models.schemas import PrescriptionExtracted
from app.core.config.config import settings
from app.core.utils.disclaimer import MEDICAL_DISCLAIMER

# Get logger without configuring at module level
logger = logging.getLogger(__name__)

# Constants
DEFAULT_MAX_RETRIES = 1
DEFAULT_BACKOFF_FACTOR = 2.0
DEFAULT_TIMEOUT = 10
MAX_TOKENS = 1024
CLIENT_ERROR_MIN = 400
CLIENT_ERROR_MAX = 500

# API Endpoints
ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

# Date placeholder values that should be treated as None
INVALID_DATE_VALUES = {"YYYY-MM-DD", "NULL", "NONE", "UNKNOWN"}


@dataclass
class APIConfig:
    """Configuration for an AI API provider."""
    name: str
    url: str
    api_key: Optional[str]
    model: str
    max_retries: int
    headers_builder: Callable[[str], Dict[str, str]]
    response_parser: Callable[[Dict[str, Any]], str]


def retry_with_backoff(
    max_retries: int = DEFAULT_MAX_RETRIES,
    backoff_factor: float = DEFAULT_BACKOFF_FACTOR,
    timeout: int = DEFAULT_TIMEOUT
):
    """
    Decorator for retrying failed API calls with exponential backoff.
    
    Args:
        max_retries: Maximum number of retry attempts
        backoff_factor: Exponential backoff multiplier
        timeout: Request timeout in seconds
    
    Raises:
        The last exception encountered after all retries are exhausted
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                
                except requests.exceptions.Timeout:
                    last_exception = RuntimeError(
                        f"{func.__name__} timed out after {timeout}s"
                    )
                    _handle_retry(func.__name__, attempt, max_retries, last_exception, backoff_factor)
                
                except requests.exceptions.RequestException as e:
                    # Don't retry on 4xx client errors, only 5xx and network errors
                    if _is_client_error(e):
                        raise
                    last_exception = e
                    _handle_retry(func.__name__, attempt, max_retries, e, backoff_factor)
                
                except Exception as e:
                    last_exception = e
                    _handle_retry(func.__name__, attempt, max_retries, e, backoff_factor)
            
            # All retries exhausted
            logger.error(f"{func.__name__} failed after {max_retries} attempts")
            if last_exception is None:
                raise RuntimeError(f"{func.__name__} failed with unknown error")
            raise last_exception
        
        return wrapper
    return decorator


def _is_client_error(exception: requests.exceptions.RequestException) -> bool:
    """
    Check if the exception represents a 4xx client error.
    
    Args:
        exception: The request exception to check
    
    Returns:
        True if it's a 4xx error, False otherwise
    """
    # Safely check for response and status_code attributes
    if exception.response is None:
        return False
    
    status_code = getattr(exception.response, 'status_code', None)
    if status_code is None:
        return False
    
    return CLIENT_ERROR_MIN <= status_code < CLIENT_ERROR_MAX


def _handle_retry(
    func_name: str,
    attempt: int,
    max_retries: int,
    exception: Exception,
    backoff_factor: float
) -> None:
    """
    Handle retry logic including logging and sleeping.
    
    Args:
        func_name: Name of the function being retried
        attempt: Current attempt number (0-indexed)
        max_retries: Maximum number of retries
        exception: The exception that triggered the retry
        backoff_factor: Exponential backoff multiplier
    """
    if attempt < max_retries - 1:
        wait_time = backoff_factor ** attempt
        logger.warning(
            f"{func_name} attempt {attempt + 1}/{max_retries} failed: {str(exception)}. "
            f"Retrying in {wait_time}s..."
        )
        time.sleep(wait_time)


def get_extraction_prompt(ai_ready_text: str) -> str:
    """
    Generate the extraction prompt for AI providers.
    
    Args:
        ai_ready_text: Cleaned OCR text from prescription image
    
    Returns:
        Formatted prompt string
    """
    return f"""
You are a medical text extraction engine.
You do NOT provide medical advice.

Extract structured information from the prescription text below.

STRICT RULES:
- Use ONLY information explicitly present in the text
- Do NOT infer or guess missing values
- Do NOT expand abbreviations
- Do NOT correct medicine names
- If a field is missing, set it to null
- Output MUST be valid JSON ONLY
- Follow the exact JSON structure

IMPORTANT SAFETY RULES:
- You are NOT a doctor.
- You MUST NOT provide medical advice.
- You MUST NOT suggest treatments or medications.
- You ONLY extract information explicitly written in the prescription.
- If information is missing or unclear, return null.

DISCLAIMER (MANDATORY – DO NOT REPHRASE):
"{MEDICAL_DISCLAIMER}"

TASK:
Extract structured information from the prescription text below.

OUTPUT RULES:
- Output VALID JSON ONLY
- Follow the exact schema
- Do NOT add explanations or comments

JSON STRUCTURE:
{{
  "doctor_name": null,
  "hospital": null,
  "date": "YYYY-MM-DD",
  "patient_name": null,
  "diagnosis": null,
  "medicines": [
    {{
      "name": null,
      "dosage": null,
      "frequency": null,
      "duration": null,
      "instructions": null
    }}
  ],
  "tests_advised": [],
  "follow_up": null
}}

PRESCRIPTION TEXT:
\"\"\"
{ai_ready_text}
\"\"\"
"""


def parse_json_response(text_output: str) -> Dict[str, Any]:
    """
    Parse JSON response from AI provider, handling markdown code blocks.
    
    Args:
        text_output: Raw text output from AI provider
    
    Returns:
        Parsed JSON dictionary
    
    Raises:
        json.JSONDecodeError: If JSON parsing fails
    """
    text_output = text_output.strip()
    
    # Remove markdown code blocks if present
    if "```json" in text_output:
        try:
            text_output = text_output.split("```json")[1].split("```")[0].strip()
        except IndexError:
            logger.warning("Malformed ```json block, attempting to parse anyway")
    elif "```" in text_output:
        try:
            text_output = text_output.split("```")[1].split("```")[0].strip()
        except IndexError:
            logger.warning("Malformed ``` block, attempting to parse anyway")
    
    try:
        return json.loads(text_output)
    except json.JSONDecodeError as e:
        logger.error(
            f"Failed to parse JSON at position {e.pos}: {e.msg}\n"
            f"Problematic text: {text_output[:200]}..."
        )
        raise


def _call_ai_provider(config: APIConfig, prompt: str) -> Dict[str, Any]:
    """
    Generic function to call any AI provider with standardized error handling.
    
    Args:
        config: API configuration for the provider
        prompt: The extraction prompt
    
    Returns:
        Parsed JSON response
    
    Raises:
        RuntimeError: If API key is not set
        requests.exceptions.RequestException: On API errors
    """
    @retry_with_backoff(
        max_retries=config.max_retries,
        backoff_factor=DEFAULT_BACKOFF_FACTOR,
        timeout=DEFAULT_TIMEOUT
    )
    def _make_request():
        if not config.api_key:
            raise RuntimeError(f"{config.name}_API_KEY not set")
        
        logger.info(f"Attempting extraction with {config.name}...")
        
        payload: Dict[str, Any] = {
            "model": config.model,
            "messages": [{"role": "user", "content": prompt}]
        }
        
        # Add max_tokens for Anthropic
        if config.name == "Anthropic":
            payload["max_tokens"] = MAX_TOKENS
        
        response = requests.post(
            config.url,
            headers=config.headers_builder(config.api_key),
            json=payload,
            timeout=DEFAULT_TIMEOUT
        )
        
        if response.status_code != 200:
            logger.error(
                f"{config.name} API error: {response.status_code} - {response.text}"
            )
        
        response.raise_for_status()
        response_text = config.response_parser(response.json())
        return parse_json_response(response_text)
    
    return _make_request()


# Header builders for each provider
def _build_anthropic_headers(api_key: str) -> Dict[str, str]:
    """Build headers for Anthropic API."""
    return {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }


def _build_openrouter_headers(api_key: str) -> Dict[str, str]:
    """Build headers for OpenRouter API."""
    return {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/hynko431/MedVault",
        "X-Title": "MedVault AI OCR",
    }


def _build_groq_headers(api_key: str) -> Dict[str, str]:
    """Build headers for Groq API."""
    return {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }


# Response parsers for each provider
def _parse_anthropic_response(response_json: Dict[str, Any]) -> str:
    """Parse Anthropic API response to extract text."""
    return response_json["content"][0]["text"]


def _parse_openai_format_response(response_json: Dict[str, Any]) -> str:
    """Parse OpenAI-format API response to extract text."""
    return response_json["choices"][0]["message"]["content"]


def try_anthropic(prompt: str) -> Dict[str, Any]:
    """
    Try extraction using Anthropic API.
    
    Args:
        prompt: The extraction prompt
    
    Returns:
        Parsed extraction result
    """
    config = APIConfig(
        name="Anthropic",
        url=ANTHROPIC_API_URL,
        api_key=settings.ANTHROPIC_API_KEY,
        model=settings.ANTHROPIC_MODEL,
        max_retries=1,
        headers_builder=_build_anthropic_headers,
        response_parser=_parse_anthropic_response
    )
    return _call_ai_provider(config, prompt)


def try_openrouter(prompt: str) -> Dict[str, Any]:
    """
    Try extraction using OpenRouter API.
    
    Args:
        prompt: The extraction prompt
    
    Returns:
        Parsed extraction result
    """
    config = APIConfig(
        name="OpenRouter",
        url=OPENROUTER_API_URL,
        api_key=settings.OPENROUTER_API_KEY,
        model=settings.OPENROUTER_MODEL,
        max_retries=1,
        headers_builder=_build_openrouter_headers,
        response_parser=_parse_openai_format_response
    )
    return _call_ai_provider(config, prompt)


def try_groq(prompt: str) -> Dict[str, Any]:
    """
    Try extraction using Groq API.
    
    Args:
        prompt: The extraction prompt
    
    Returns:
        Parsed extraction result
    """
    config = APIConfig(
        name="Groq",
        url=GROQ_API_URL,
        api_key=settings.GROQ_API_KEY,
        model=settings.GROQ_MODEL,
        max_retries=2,
        headers_builder=_build_groq_headers,
        response_parser=_parse_openai_format_response
    )
    return _call_ai_provider(config, prompt)


def extract_structured_data(cleaned_text: str) -> Dict[str, Any]:
    """
    Extract structured prescription data using AI provider fallback chain.
    
    Args:
        cleaned_text: Cleaned OCR text from prescription image
    
    Returns:
        Extracted data as dictionary
    
    Raises:
        RuntimeError: When all AI providers fail
    """
    prompt = get_extraction_prompt(cleaned_text)
    errors = []
    
    # Provider fallback chain
    providers = [
        ("Anthropic", try_anthropic),
        ("OpenRouter", try_openrouter),
        ("Groq", try_groq),
    ]
    
    for provider_name, provider_func in providers:
        try:
            result = provider_func(prompt)
            logger.info(f"✅ {provider_name} extraction successful")
            return result
        except Exception as e:
            error_msg = f"{provider_name} failed: {str(e)}"
            logger.warning(error_msg)
            errors.append(error_msg)
    
    # All providers failed
    error_summary = " | ".join(errors)
    logger.error(f"🚨 All AI extraction providers failed: {error_summary}")
    raise RuntimeError(f"All AI providers failed. Errors: {error_summary}")


def _clean_date_field(data: Dict[str, Any]) -> None:
    """
    Clean date field by replacing placeholder values with None.
    
    Args:
        data: Dictionary containing prescription data (modified in-place)
    """
    if data.get("date"):
        date_val = str(data["date"]).strip().upper()
        if date_val in INVALID_DATE_VALUES:
            data["date"] = None


def validate_extracted_json(data: Any) -> PrescriptionExtracted:
    """
    Validate extracted JSON data against PrescriptionExtracted schema.
    
    Args:
        data: Dictionary or dict-like object from AI extraction
    
    Returns:
        Validated PrescriptionExtracted object
    
    Raises:
        RuntimeError: When validation fails
    """
    # Handle already-validated data
    if isinstance(data, PrescriptionExtracted):
        return data
    
    # Type check
    if not isinstance(data, dict):
        raise RuntimeError(
            f"Expected dict or PrescriptionExtracted, got {type(data).__name__}"
        )
    
    try:
        # Clean up date field
        _clean_date_field(data)
        
        logger.info("Validating extracted data schema...")
        validated = PrescriptionExtracted(**data)
        logger.info(
            f"✅ Validation successful. "
            f"Extracted {len(validated.medicines)} medicine(s)"
        )
        return validated
    
    except ValidationError as e:
        logger.error(f"Schema validation failed: {e.json()}")
        raise RuntimeError(
            f"Extracted JSON failed schema validation: {str(e)}"
        ) from e
    
    except Exception as e:
        logger.error(f"Unexpected validation error: {str(e)}", exc_info=True)
        raise RuntimeError(f"Validation error: {str(e)}") from e