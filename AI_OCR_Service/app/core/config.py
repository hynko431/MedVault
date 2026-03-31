import os
from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    PROJECT_NAME: str = "AI OCR & Search Service"

    # Anthropic Claude
    ANTHROPIC_API_KEY: str

    # Google Cloud Vision — path to service account JSON
    GOOGLE_APPLICATION_CREDENTIALS: str

    # Elasticsearch
    ELASTICSEARCH_HOST: str = "http://elasticsearch:9200"
    ELASTICSEARCH_INDEX: str = "prescriptions"

    # Service port (informational)
    API_PORT: int = 8000

    class Config:
        # Look for .env relative to this file's root (AI_OCR_Service/.env)
        env_file = str(Path(__file__).resolve().parent.parent.parent / ".env")
        env_file_encoding = "utf-8"
        # Allow extra env vars without failing
        extra = "ignore"


settings = Settings()
