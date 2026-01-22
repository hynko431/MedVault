import os
from dotenv import load_dotenv
from pathlib import Path

# Load .env file from the root of the AI_OCR_Service directory
env_path = Path(__file__).resolve().parent.parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

class Settings:
    PROJECT_NAME: str = "AI OCR & Search Service"
    
    # Google Cloud Vision
    GOOGLE_APPLICATION_CREDENTIALS: str = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    
    # Anthropic
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY")
    
    # Elasticsearch
    ELASTICSEARCH_HOST: str = os.getenv("ELASTICSEARCH_HOST", "http://localhost:9200")

    def get_masked_key(self, key_name: str) -> str:
        val = getattr(self, key_name, "")
        if not val:
            return "NOT SET"
        if len(val) <= 8:
            return "***"
        return f"{val[:4]}...{val[-4:]}"

settings = Settings()
