import os
import requests
import json
import logging
from pydantic import ValidationError
from app.models.schemas import PrescriptionExtracted
from app.core.config import settings

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

JSON STRUCTURE:
{{
  "doctor_name": null,
  "hospital": null,
  "date":"YYYY-MM-DD",
  "patient_name":null,
  "medicines": [
    {{
      "name": null,
      "dosage": null,
      "frequency": null,
      "duration": null,
      "instructions":null
    }}
  ],
  "tests_advised":[],
  "follow_up": null
}}

PRESCRIPTION TEXT:
\"\"\"
{ai_ready_text}
\"\"\"
"""

def parse_json_response(text_output: str) -> dict:
    # Clean markdown blocks if present
    if "```json" in text_output:
        text_output = text_output.split("```json")[1].split("```")[0].strip()
    elif "```" in text_output:
        text_output = text_output.split("```")[1].split("```")[0].strip()
    
    return json.loads(text_output)

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
    response.raise_for_status()
    return parse_json_response(response.json()["content"][0]["text"])

def try_openrouter(prompt: str) -> dict:
    if not settings.OPENROUTER_API_KEY:
        raise RuntimeError("OPENROUTER_API_KEY not set")
    
    logger.info("Attempting extraction with OpenRouter...")
    headers = {
        "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": settings.OPENROUTER_MODEL,
        "messages": [{"role": "user", "content": prompt}]
    }
    response = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload, timeout=30)
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
        logger.error(err)
        errors.append(err)

    # 2. Try OpenRouter
    try:
        return try_openrouter(prompt)
    except Exception as e:
        err = f"OpenRouter failed: {str(e)}"
        logger.error(err)
        errors.append(err)

    # 3. Try Groq
    try:
        return try_groq(prompt)
    except Exception as e:
        err = f"Groq failed: {str(e)}"
        logger.error(err)
        errors.append(err)

    raise RuntimeError(f"All AI providers failed. Errors: {'; '.join(errors)}")

def validate_extracted_json(data: dict) -> PrescriptionExtracted:
    try:
        return PrescriptionExtracted(**data)
    except ValidationError as e:
        raise RuntimeError("AI JSON failed schema validation") from e