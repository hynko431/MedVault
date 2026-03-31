import json
import anthropic
from pydantic import ValidationError
from app.models.schemas import PrescriptionExtracted
from app.core.config import settings

CLAUDE_MODEL = "claude-3-5-sonnet-20240620"

EXTRACTION_PROMPT = """
You are a medical text extraction engine.
You do NOT provide medical advice.

Extract structured information from the prescription text below.

STRICT RULES:
- Use ONLY information explicitly present in the text
- Do NOT infer or guess missing values
- Do NOT expand abbreviations
- Do NOT correct medicine names
- If a field is missing, set it to null
- Output MUST be valid JSON ONLY — no markdown, no explanation
- Follow the exact JSON structure below

JSON STRUCTURE:
{{
  "doctor_name": null,
  "hospital": null,
  "patient_name": null,
  "date": null,
  "medicines": [
    {{
      "name": null,
      "strength": null,
      "dosage": null,
      "frequency": null,
      "duration": null,
      "route": null
    }}
  ]
}}

PRESCRIPTION TEXT:
\"\"\"
{cleaned_text}
\"\"\"
"""


def extract_structured_data(cleaned_text: str) -> dict:
    """
    Call Claude via the official Anthropic SDK to extract structured
    prescription data from cleaned OCR text.
    """
    api_key = settings.ANTHROPIC_API_KEY
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY is not set in configuration.")

    client = anthropic.Anthropic(api_key=api_key)

    prompt = EXTRACTION_PROMPT.format(cleaned_text=cleaned_text)

    try:
        message = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )
    except anthropic.APIConnectionError as e:
        raise RuntimeError(f"Could not connect to Anthropic API: {str(e)}")
    except anthropic.RateLimitError as e:
        raise RuntimeError(f"Anthropic rate limit exceeded: {str(e)}")
    except anthropic.APIStatusError as e:
        raise RuntimeError(f"Anthropic API error {e.status_code}: {e.message}")

    text_output = message.content[0].text

    # Strip any accidental markdown fences Claude might add
    if "```json" in text_output:
        text_output = text_output.split("```json")[1].split("```")[0].strip()
    elif "```" in text_output:
        text_output = text_output.split("```")[1].split("```")[0].strip()

    try:
        parsed = json.loads(text_output)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Failed to parse Claude JSON response: {str(e)}\nRaw output: {text_output}")

    return parsed


def validate_extracted_json(data: dict) -> PrescriptionExtracted:
    """Validate Claude's parsed dict against the PrescriptionExtracted schema."""
    try:
        validated = PrescriptionExtracted(**data)
    except ValidationError as e:
        raise RuntimeError("Claude JSON failed schema validation") from e
    return validated
