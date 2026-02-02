import os
import requests
import json
import logging
import time
from functools import wraps
from typing import Dict, Any, Optional, List
from pydantic import ValidationError
from app.models.schemas import DynamicPrescriptionExtracted
from app.core.config import settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Medical Disclaimer for AI
MEDICAL_DISCLAIMER = "This is an AI-extracted summary. Please verify with the original prescription. Not a medical diagnosis."

def retry_with_backoff(max_retries: int = 1, backoff_factor: float = 2.0, timeout: int = 10):
    """
    Decorator for retrying failed API calls with exponential backoff.
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
                        logger.warning(f"{func.__name__} attempt {attempt + 1}/{max_retries} timed out. Retrying in {wait_time}s...")
                        time.sleep(wait_time)
                except requests.exceptions.RequestException as e:
                    if hasattr(e, 'response') and e.response is not None:
                        status_code = e.response.status_code
                        if status_code in (401, 403):
                            logger.error(f"Authentication failed ({status_code}). Failing fast.")
                            raise
                        elif 400 <= status_code < 500:
                            logger.error(f"Client error ({status_code}). Failing fast.")
                            raise
                        elif status_code >= 500:
                            last_exception = e
                            if attempt < max_retries - 1:
                                wait_time = backoff_factor ** attempt
                                logger.warning(f"{func.__name__} attempt {attempt + 1}/{max_retries} server error ({status_code}). Retrying in {wait_time}s...")
                                time.sleep(wait_time)
                    else:
                        last_exception = e
                        if attempt < max_retries - 1:
                            wait_time = backoff_factor ** attempt
                            logger.warning(f"{func.__name__} attempt {attempt + 1}/{max_retries} network error: {str(e)}. Retrying in {wait_time}s...")
                            time.sleep(wait_time)
                except Exception as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        wait_time = backoff_factor ** attempt
                        logger.warning(f"{func.__name__} attempt {attempt + 1}/{max_retries} failed: {str(e)}. Retrying in {wait_time}s...")
                        time.sleep(wait_time)
            
            logger.error(f"{func.__name__} failed after {max_retries} attempts")
            raise last_exception
        return wrapper
    return decorator

def get_dynamic_extraction_prompt(ai_ready_text: str, extraction_mode: str = "dynamic") -> str:
    """
    Generate a dynamic extraction prompt that adapts to prescription content.
    """
    if extraction_mode == "dynamic":
        return f"""You are an advanced medical prescription extraction engine with dynamic field detection.

CRITICAL INSTRUCTIONS:
1. Extract ALL information present in the prescription, even if it doesn't fit standard fields
2. Organize information into logical categories (patient, doctor, hospital, vitals, medicines, etc.)
3. NEVER invent or infer missing information
4. Preserve exact text from prescription (don't "fix" medicine names or abbreviations)
5. If a field is unclear or missing, use null
6. Output MUST be valid JSON

SAFETY RULES:
- You are NOT a doctor and do NOT provide medical advice
- You ONLY extract information explicitly written in the prescription
- If information is ambiguous, extract it as-is without interpretation

DISCLAIMER: "{MEDICAL_DISCLAIMER}"

DYNAMIC EXTRACTION GUIDELINES:

1. **Patient Information** - Extract into "patient" object:
   - name, age, gender, phone, email, address
   - patient_id, insurance_id, blood_group, allergies
   - ANY other patient-related fields you find

2. **Doctor Information** - Extract into "doctor" object:
   - name (or names if multiple doctors)
   - qualification, qualifications (MBBS, MD, etc.)
   - specialization, registration_number
   - ANY other doctor-related fields

3. **Hospital/Clinic** - Extract into "hospital" object:
   - name, address, phone, email, website
   - registration_number
   - ANY other facility-related fields

4. **Vital Signs** - Extract into "vitals" object:
   - blood_pressure (BP), pulse_rate (PR), temperature
   - weight, height, bmi, oxygen_saturation
   - ANY other vital signs you find

5. **Medical Content**:
   - diagnosis: List of diagnoses (k/c/o, c/o, etc.)
   - symptoms: Patient complaints
   - medical_history: h/o fields
   - medicines: DETAILED list (see structure below)
   - tests_advised: Investigations ordered
   - advice: General instructions
   - precautions: Warnings or precautions
   - dietary_restrictions: Food-related advice
   - follow_up: Next visit information

6. **Medicine Structure** (extract ALL available fields):
   {{
     "name": "Medicine name (EXACT as written)",
     "dosage": "Dose amount (5mg, 75mcg, etc.)",
     "frequency": "How often (1-0-1, BD, TDS, etc.)",
     "duration": "How long (30 days, 1 week, etc.)",
     "instructions": "Special instructions (before food, etc.)",
     "form": "tablet/capsule/syrup/injection/etc.",
     "route": "oral/topical/IV/etc.",
     "timing": "before food/after food/bedtime/etc.",
     "quantity": "Total quantity prescribed",
     ... any other medicine-related fields
   }}

7. **Dynamic Fields**:
   - If you find ANY information that doesn't fit the above categories,
     add it to "additional_fields" with descriptive key names

OUTPUT FORMAT (JSON only, no markdown):
{{
  "patient": {{
    "name": "...",
    "age": "...",
    "gender": "...",
    ... (any patient fields found)
  }},
  "doctor": {{
    "names": ["Dr. Name 1", "Dr. Name 2"],
    "qualifications": ["MBBS", "MD"],
    "registration_numbers": ["12345"],
    ... (any doctor fields found)
  }},
  "hospital": {{
    "name": "...",
    "address": "...",
    ... (any hospital fields found)
  }},
  "vitals": {{
    "blood_pressure": "...",
    "pulse_rate": "...",
    ... (any vitals found)
  }},
  "diagnosis": ["...", "..."],
  "symptoms": ["...", "..."],
  "medical_history": ["...", "..."],
  "medicines": [
    {{
      "name": "...",
      "dosage": "...",
      "frequency": "...",
      "duration": "...",
      "instructions": "...",
      ... (any other medicine fields)
    }}
  ],
  "tests_advised": ["...", "..."],
  "date": "YYYY-MM-DD" or null,
  "follow_up": "...",
  "advice": ["...", "..."],
  "precautions": ["...", "..."],
  "dietary_restrictions": ["...", "..."],
  "additional_fields": {{
    "any_other_field": "value",
    ...
  }}
}}

PRESCRIPTION TEXT:
\"\"\"
{ai_ready_text}
\"\"\"

IMPORTANT: 
- Output ONLY valid JSON, no markdown code blocks, no explanations
- Extract EVERYTHING you see, organize it logically
- Preserve exact spelling and formatting from the prescription
- Use null for missing fields, empty arrays [] for empty lists
"""
    else:  # strict mode
        return f"""You are a medical prescription extraction engine (strict mode).

Extract ONLY the following standardized fields from the prescription:

STRICT FIELD LIST:
- doctor_name: List of doctor names
- hospital_name: Hospital/clinic name
- date: Prescription date (YYYY-MM-DD format)
- patient_name: Patient name
- diagnosis: Diagnosis or condition
- medicines: List with name, dosage, frequency, duration, instructions
- tests_advised: List of tests ordered
- follow_up: Next visit date/instructions

RULES:
- Use ONLY information explicitly present
- Do NOT infer or guess
- Output MUST be valid JSON ONLY

DISCLAIMER: "{MEDICAL_DISCLAIMER}"

JSON STRUCTURE:
{{
  "doctor_name": [],
  "hospital_name": null,
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
    """
    Parse JSON from AI response, handling markdown code blocks.
    """
    text_output = text_output.strip()
    if "```json" in text_output:
        text_output = text_output.split("```json")[1].split("```")[0].strip()
    elif "```" in text_output:
        text_output = text_output.split("```")[1].split("```")[0].strip()
    
    try:
        return json.loads(text_output)
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON response: {text_output[:500]}")
        raise

def try_anthropic(prompt: str) -> dict:
    @retry_with_backoff(max_retries=2, backoff_factor=2.0, timeout=10)
    def _call_anthropic():
        if not settings.ANTHROPIC_API_KEY:
            raise RuntimeError("ANTHROPIC_API_KEY not set")
        
        logger.info("🤖 Attempting extraction with Anthropic (Claude)...")
        headers = {
            "x-api-key": settings.ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        payload = {
            "model": settings.ANTHROPIC_MODEL,
            "max_tokens": 2048,
            "temperature": 0.1,
            "messages": [{"role": "user", "content": prompt}]
        }
        response = requests.post("https://api.anthropic.com/v1/messages", headers=headers, json=payload, timeout=30)
        if response.status_code != 200:
            logger.error(f"Anthropic API error: {response.status_code} - {response.text}")
        response.raise_for_status()
        return parse_json_response(response.json()["content"][0]["text"])
    return _call_anthropic()

def try_groq(prompt: str) -> dict:
    @retry_with_backoff(max_retries=2, backoff_factor=2.0, timeout=10)
    def _call_groq():
        if not settings.GROQ_API_KEY:
            raise RuntimeError("GROQ_API_KEY not set")
        
        logger.info("⚡ Attempting extraction with Groq...")
        headers = {
            "Authorization": f"Bearer {settings.GROQ_API_KEY}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": settings.GROQ_MODEL,
            "temperature": 0.1,
            "messages": [{"role": "user", "content": prompt}]
        }
        response = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload, timeout=30)
        if response.status_code != 200:
            logger.error(f"Groq API error: {response.status_code} - {response.text}")
        response.raise_for_status()
        return parse_json_response(response.json()["choices"][0]["message"]["content"])
    return _call_groq()

def try_openrouter(prompt: str) -> dict:
    @retry_with_backoff(max_retries=2, backoff_factor=2.0, timeout=10)
    def _call_openrouter():
        if not settings.OPENROUTER_API_KEY:
            raise RuntimeError("OPENROUTER_API_KEY not set")
        
        logger.info("🌐 Attempting extraction with OpenRouter...")
        headers = {
            "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/hynko431/MedVault",
            "X-Title": "MedVault AI OCR",
        }
        payload = {
            "model": settings.OPENROUTER_MODEL,
            "temperature": 0.1,
            "messages": [{"role": "user", "content": prompt}]
        }
        response = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload, timeout=30)
        if response.status_code != 200:
            logger.error(f"OpenRouter API error: {response.status_code} - {response.text}")
        response.raise_for_status()
        return parse_json_response(response.json()["choices"][0]["message"]["content"])
    return _call_openrouter()

def extract_structured_data(
    cleaned_text: str, 
    extraction_mode: str = "dynamic",
    provider_priority: Optional[List[str]] = None
) -> dict:
    """
    Extract structured prescription data using AI provider fallback chain.
    """
    prompt = get_dynamic_extraction_prompt(cleaned_text, extraction_mode)
    errors = []
    
    if provider_priority is None:
        provider_priority = ["anthropic", "openrouter", "groq"]
    
    providers = {
        "anthropic": try_anthropic,
        "groq": try_groq,
        "openrouter": try_openrouter
    }
    
    for provider_name in provider_priority:
        if provider_name not in providers:
            continue
        try:
            result = providers[provider_name](prompt)
            logger.info(f"✅ {provider_name.capitalize()} extraction successful (mode: {extraction_mode})")
            result['extraction_metadata'] = {
                'provider': provider_name,
                'mode': extraction_mode,
                'timestamp': time.time()
            }
            return result
        except Exception as e:
            err = f"{provider_name.capitalize()} failed: {str(e)}"
            logger.warning(err)
            errors.append(err)
    
    raise RuntimeError(f"All AI providers failed. Errors: {' | '.join(errors)}")

def validate_extracted_json(
    data: Any, 
    strict: bool = False
) -> DynamicPrescriptionExtracted:
    """
    Validate extracted JSON data against dynamic prescription schema.
    """
    if isinstance(data, DynamicPrescriptionExtracted):
        return data
    
    if not isinstance(data, dict):
        raise RuntimeError(f"Expected dict, got {type(data).__name__}")
    
    try:
        logger.info("🔍 Validating extracted data against dynamic schema...")
        validated = DynamicPrescriptionExtracted(**data)
        logger.info("✅ Validation successful!")
        return validated
    except ValidationError as e:
        error_msg = f"Schema validation failed: {e.json()}"
        logger.error(error_msg)
        if strict:
            raise RuntimeError(error_msg) from e
        else:
            logger.warning("⚠️ Continuing with partial validation...")
            try:
                minimal_data = {
                    "medicines": data.get("medicines", []),
                    "tests_advised": data.get("tests_advised", []),
                    "additional_fields": data
                }
                return DynamicPrescriptionExtracted(**minimal_data)
            except Exception:
                raise RuntimeError(error_msg) from e
    except Exception as e:
        logger.error(f"Unexpected validation error: {str(e)}", exc_info=True)
        raise RuntimeError(f"Validation error: {str(e)}") from e
