import os
import requests
import json
import logging
import time
from functools import wraps
from pydantic import ValidationError
from app.models.schemas import PrescriptionExtracted
from app.core.config import settings
from app.core.disclaimer import MEDICAL_DISCLAIMER

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def retry_with_backoff(max_retries: int = 1, backoff_factor: float = 2.0, timeout: int = 5):
    """
    Decorator for retrying failed API calls with exponential backoff.
    
    Implements smart fast-fail strategy:
    - 401/403 (auth errors): No retry, fail immediately
    - 4xx (client errors): No retry, fail immediately
    - 5xx/timeout: Retry with exponential backoff
    
    Args:
        max_retries: Maximum number of retry attempts
        backoff_factor: Exponential backoff multiplier
        timeout: Request timeout in seconds
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except requests.exceptions.Timeout:
                    last_exception = RuntimeError(f"{func.__name__} timed out after {timeout}s")
                    if attempt < max_retries - 1:
                        wait_time = backoff_factor ** attempt
                        logger.warning(
                            f"{func.__name__} attempt {attempt + 1}/{max_retries} timed out. "
                            f"Retrying in {wait_time}s..."
                        )
                        time.sleep(wait_time)
                except requests.exceptions.RequestException as e:
                    # Fast-fail on authentication or client errors (401, 403, 4xx)
                    if hasattr(e, 'response') and e.response is not None:
                        status_code = e.response.status_code
                        if status_code in (401, 403):
                            logger.error(f"Authentication failed ({status_code}). Failing fast without retry.")
                            raise
                        elif 400 <= status_code < 500:
                            logger.error(f"Client error ({status_code}). Failing fast without retry.")
                            raise
                        elif status_code >= 500:
                            # Server errors: retry
                            last_exception = e
                            if attempt < max_retries - 1:
                                wait_time = backoff_factor ** attempt
                                logger.warning(
                                    f"{func.__name__} attempt {attempt + 1}/{max_retries} server error ({status_code}). "
                                    f"Retrying in {wait_time}s..."
                                )
                                time.sleep(wait_time)
                    else:
                        # Network error (no response): retry
                        last_exception = e
                        if attempt < max_retries - 1:
                            wait_time = backoff_factor ** attempt
                            logger.warning(
                                f"{func.__name__} attempt {attempt + 1}/{max_retries} network error: {str(e)}. "
                                f"Retrying in {wait_time}s..."
                            )
                            time.sleep(wait_time)
                except Exception as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        wait_time = backoff_factor ** attempt
                        logger.warning(
                            f"{func.__name__} attempt {attempt + 1}/{max_retries} failed: {str(e)}. "
                            f"Retrying in {wait_time}s..."
                        )
                        time.sleep(wait_time)
            
            logger.error(f"{func.__name__} failed after {max_retries} attempts")
            raise last_exception # type: ignore
        return wrapper
    return decorator

def get_extraction_prompt(ai_ready_text: str) -> str:
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
  "doctor_name": [],
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

def parse_json_response(text_output: str) -> dict:
    # Clean markdown blocks if present
    text_output = text_output.strip()
    if "```json" in text_output:
        text_output = text_output.split("```json")[1].split("```")[0].strip()
    elif "```" in text_output:
        text_output = text_output.split("```")[1].split("```")[0].strip()
    
    try:
        return json.loads(text_output)
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON: {text_output}")
        raise e

def try_anthropic(prompt: str) -> dict:
    @retry_with_backoff(max_retries=1, backoff_factor=2.0, timeout=5)
    def _call_anthropic():
        if not settings.ANTHROPIC_API_KEY:
            raise RuntimeError("ANTHROPIC_API_KEY not set")
        
        logger.info("Attempting extraction with Anthropic...")
        headers = {
            "x-api-key": settings.ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        payload = {
            "model": settings.ANTHROPIC_MODEL,
            "max_tokens": 1024,
            "messages": [{"role": "user", "content": prompt}]
        }
        response = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers=headers,
            json=payload,
            timeout=10
        )
        if response.status_code != 200:
            logger.error(f"Anthropic API error: {response.status_code} - {response.text}")
        response.raise_for_status()
        return parse_json_response(response.json()["content"][0]["text"])
    
    return _call_anthropic()

def try_groq(prompt: str) -> dict:
    @retry_with_backoff(max_retries=2, backoff_factor=2.0, timeout=5)
    def _call_groq():
        if not settings.GROQ_API_KEY:
            raise RuntimeError("GROQ_API_KEY not set")
        
        logger.info("Attempting extraction with Groq...")
        headers = {
            "Authorization": f"Bearer {settings.GROQ_API_KEY}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": settings.GROQ_MODEL,
            "messages": [{"role": "user", "content": prompt}]
        }
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=10
        )
        if response.status_code != 200:
            logger.error(f"Groq API error: {response.status_code} - {response.text}")
        response.raise_for_status()
        return parse_json_response(response.json()["choices"][0]["message"]["content"])
    
    return _call_groq()

def try_openrouter(prompt: str) -> dict:
    @retry_with_backoff(max_retries=1, backoff_factor=2.0, timeout=5)
    def _call_openrouter():
        if not settings.OPENROUTER_API_KEY:
            raise RuntimeError("OPENROUTER_API_KEY not set")
        
        logger.info("Attempting extraction with OpenRouter...")
        # OpenRouter recommends including these headers
        headers = {
            "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/hynko431/MedVault",
            "X-Title": "MedVault AI OCR",
        }
        payload = {
            "model": settings.OPENROUTER_MODEL,
            "messages": [{"role": "user", "content": prompt}]
        }
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=10
        )
        if response.status_code != 200:
            logger.error(f"OpenRouter API error: {response.status_code} - {response.text}")
        response.raise_for_status()
        return parse_json_response(response.json()["choices"][0]["message"]["content"])
    
    return _call_openrouter()

def extract_structured_data(cleaned_text: str) -> dict:
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

    # 1️⃣ Try Anthropic
    try:
        result = try_anthropic(prompt)
        logger.info("✅ Anthropic extraction successful")
        return result
    except Exception as e:
        err = f"Anthropic failed: {str(e)}"
        logger.warning(err)
        errors.append(err)
    
    # 2️⃣ Try OpenRouter
    try:
        result = try_openrouter(prompt)
        logger.info("✅ OpenRouter extraction successful")
        return result
    except Exception as e:
        err = f"OpenRouter failed: {str(e)}"
        logger.warning(err)
        errors.append(err)

    # 3️⃣ Try Groq
    try:
        result = try_groq(prompt)
        logger.info("✅ Groq extraction successful")
        return result
    except Exception as e:
        err = f"Groq failed: {str(e)}"
        logger.warning(err)
        errors.append(err)

    

    # ❌ All providers failed
    error_summary = " | ".join(errors)
    logger.error(f"🚨 All AI extraction providers failed: {error_summary}")
    raise RuntimeError(f"All AI providers failed. Errors: {error_summary}")

def validate_extracted_json(data) -> PrescriptionExtracted:
    """
    Validate extracted JSON data against PrescriptionExtracted schema.
    
    Args:
        data: Dictionary or dict-like object from AI extraction
        
    Returns:
        Validated PrescriptionExtracted object
        
    Raises:
        RuntimeError: When validation fails
    """
    # Handle both dict and PrescriptionExtracted inputs
    if isinstance(data, PrescriptionExtracted):
        return data
    
    if not isinstance(data, dict):
        raise RuntimeError(f"Expected dict or PrescriptionExtracted, got {type(data).__name__}")
    
    try:
        # Clean up date field if it contains placeholders
        if data.get("date"):
            date_val = str(data["date"]).strip().upper()
            if date_val in {"YYYY-MM-DD", "NULL", "NONE", "UNKNOWN"}:
                data["date"] = None

        logger.info(f"Validating extracted data schema...")
        validated = PrescriptionExtracted(**data)
        logger.info(f"✅ Validation successful. Extracted {len(validated.medicines)} medicines")
        return validated
    except ValidationError as e:
        logger.error(f"Schema validation failed: {e.json()}")
        raise RuntimeError(f"Extracted JSON failed schema validation: {str(e)}") from e
    except Exception as e:
        logger.error(f"Unexpected validation error: {str(e)}", exc_info=True)
        raise RuntimeError(f"Validation error: {str(e)}") from e