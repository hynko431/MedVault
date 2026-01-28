import os
import requests
import json
import logging
from pydantic import ValidationError
from app.models.schemas import PrescriptionExtracted
from app.core.config import settings
from app.core.disclaimer import MEDICAL_DISCLAIMER

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
    response = requests.post("https://api.anthropic.com/v1/messages", headers=headers, json=payload, timeout=30)
    if response.status_code != 200:
        logger.error(f"Anthropic API error: {response.status_code} - {response.text}")
    response.raise_for_status()
    return parse_json_response(response.json()["content"][0]["text"])

def try_openrouter(prompt: str) -> dict:
    if not settings.OPENROUTER_API_KEY:
        raise RuntimeError("OPENROUTER_API_KEY not set")
    
    logger.info("Attempting extraction with OpenRouter...")
    # OpenRouter recommends including these headers
    headers = {
        "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/hynko431/MedVault", # Optional
        "X-Title": "MedVault AI OCR", # Optional
    }
    payload = {
        "model": settings.OPENROUTER_MODEL,
        "messages": [{"role": "user", "content": prompt}]
    }
    response = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload, timeout=30)
    if response.status_code != 200:
        logger.error(f"OpenRouter API error: {response.status_code} - {response.text}")
    response.raise_for_status()
    return parse_json_response(response.json()["choices"][0]["message"]["content"])

def try_groq(prompt: str) -> dict:
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
    response = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload, timeout=30)
    if response.status_code != 200:
        logger.error(f"Groq API error: {response.status_code} - {response.text}")
    response.raise_for_status()
    return parse_json_response(response.json()["choices"][0]["message"]["content"])

def extract_structured_data(cleaned_text: str) -> dict:
    prompt = get_extraction_prompt(cleaned_text)
    errors = []

    # 1. Try Anthropic
    try:
        return try_anthropic(prompt)
    except Exception as e:
        err = f"Anthropic failed: {str(e)}"
        errors.append(err)

    # 2. Try OpenRouter
    try:
        return try_openrouter(prompt)
    except Exception as e:
        err = f"OpenRouter failed: {str(e)}"
        errors.append(err)

    # 3. Try Groq
    try:
        return try_groq(prompt)
    except Exception as e:
        err = f"Groq failed: {str(e)}"
        errors.append(err)

    raise RuntimeError(f"All AI providers failed. Errors: {'; '.join(errors)}")

def validate_extracted_json(data: dict) -> PrescriptionExtracted:
    try:
        # Clean up date field if it contains placeholders
        if data.get("date"):
            date_val = str(data["date"]).strip().upper()
            if date_val in {"YYYY-MM-DD", "NULL", "NONE", "UNKNOWN"}:
                data["date"] = None

        return PrescriptionExtracted(**data)
    except ValidationError as e:
        logger.error(f"Validation error: {e.json()}")
        raise RuntimeError(f"AI JSON failed schema validation: {str(e)}") from e