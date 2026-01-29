import os
from dotenv import load_dotenv
from pathlib import Path
from typing import Optional

# Load .env file from the root of the AI_OCR_Service directory
# We try multiple locations to be safe
env_locations = [
    Path(__file__).resolve().parent.parent.parent / ".env",  # Root of AI_OCR_Service
    Path.cwd() / ".env",                                     # Current working directory
]

for loc in env_locations:
    if loc.exists():
        load_dotenv(dotenv_path=loc)
        break
else:
    load_dotenv() # Fallback to default behavior

class Settings:
    PROJECT_NAME: str = "AI OCR & Search Service"
    
    # Google Cloud Vision
    GOOGLE_APPLICATION_CREDENTIALS: str = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    
    # Gemini (OCR Priority 1)
    GEMINI_API_KEY: Optional[str] = os.getenv("GEMINI_API_KEY")
    GEMINI_MODEL: str = "gemini-3-flash"
    
    # Anthropic (Extraction Priority 1)
    ANTHROPIC_API_KEY: Optional[str] = os.getenv("ANTHROPIC_API_KEY")
    ANTHROPIC_MODEL: str = "claude-3-5-sonnet-20240620"
    
    # OpenRouter (Fallback 1)
    OPENROUTER_API_KEY: Optional[str] = os.getenv("OPENROUTER_API_KEY")
    OPENROUTER_MODEL: str = "anthropic/claude-sonnet-4.5"
    
    # Groq (Fallback 2)
    GROQ_API_KEY: Optional[str] = os.getenv("GROQ_API_KEY")
    GROQ_MODEL: str = "openai/gpt-oss-safeguard-20b"
    
    # Elasticsearch
    ELASTICSEARCH_HOST: str = os.getenv("ELASTICSEARCH_HOST", "http://localhost:9200")
    ELASTICSEARCH_ENABLED: bool = os.getenv("ELASTICSEARCH_ENABLED", "false").lower() in ("true", "1", "yes")

    def get_masked_key(self, key_name: str) -> str:
        if val := getattr(self, key_name, ""):
            return "***" if len(val) <= 8 else f"{val[:4]}...{val[-4:]}"
        else:
            return "NOT SET"

settings = Settings()
