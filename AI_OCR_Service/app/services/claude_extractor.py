import os
import requests
import json
from pydantic import ValidationError
from app.models.schemas import PrescriptionExtracted
from app.core.config import settings

CLAUDE_API_URL = "https://api.anthropic.com/v1/messages"
CLAUDE_MODEL = "claude-3-5-sonnet-20240620"

def extract_structured_data(cleaned_text: str) -> dict:
    api_key = settings.ANTHROPIC_API_KEY
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY not set")

    prompt = f"""
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
  "medicines": [
    {{
      "name": null,
      "strength": null,
      "dosage": null,
      "frequency": null,
      "duration": null
    }}
  ]
}}

PRESCRIPTION TEXT:
\"\"\"
{cleaned_text}
\"\"\"
"""

    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }

    payload = {
        "model": CLAUDE_MODEL,
        "max_tokens": 512,
        "messages": [
            {"role": "user", "content": prompt}
        ]
    }

    try:
        response = requests.post(
            CLAUDE_API_URL,
            headers=headers,
            json=payload,
            timeout=30
        )
        response.raise_for_status()

        result = response.json()
        text_output = result["content"][0]["text"]

        # Claude might wrap JSON in markdown blocks
        if "```json" in text_output:
            text_output = text_output.split("```json")[1].split("```")[0].strip()
        elif "```" in text_output:
            text_output = text_output.split("```")[1].split("```")[0].strip()

        parsed = json.loads(text_output)
        return parsed
    except requests.exceptions.RequestException as e:
        error_msg = f"Claude API request failed: {str(e)}"
        if e.response is not None and e.response.status_code == 401:
            masked_key = settings.get_masked_key("ANTHROPIC_API_KEY")
            error_msg += f" (Key used: {masked_key}). Please verify your ANTHROPIC_API_KEY in the .env file."
        raise RuntimeError(error_msg)
    except (json.JSONDecodeError, KeyError, IndexError) as e:
        raise RuntimeError(f"Failed to parse Claude response: {str(e)}")


def validate_extracted_json(data: dict) -> PrescriptionExtracted:
    try:
        validated = PrescriptionExtracted(**data)
    except ValidationError as e:
        raise RuntimeError("Claude JSON failed schema validation") from e

    return validated
