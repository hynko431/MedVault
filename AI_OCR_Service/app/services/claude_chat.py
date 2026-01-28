import os
import requests
import logging
from app.core.config import settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

CLAUDE_API_URL = "https://api.anthropic.com/v1/messages"
CLAUDE_MODEL = "claude-3-5-sonnet-20240620"

def get_medicine_chat_prompt(question: str, context: dict | None = None) -> str:
    """Generate the prompt for medicine chat"""
    prompt = f"""
You are a medical information assistant.
You DO NOT diagnose.
You DO NOT give emergency advice.

Rules:
- Explain medicines in plain English
- Mention common uses, side effects, precautions
- Always include a disclaimer
- If unsure, say you are unsure

Question:
{question}
"""
    return prompt

def try_anthropic(prompt: str) -> str:
    """Try Anthropic Claude API"""
    if not settings.ANTHROPIC_API_KEY:
        raise RuntimeError("ANTHROPIC_API_KEY not set")
    
    logger.info("Attempting chat with Anthropic...")
    
    headers = {
        "x-api-key": settings.ANTHROPIC_API_KEY,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json"
    }
    
    payload = {
        "model": CLAUDE_MODEL,
        "max_tokens": 300,
        "messages": [
            {"role": "user", "content": prompt}
        ]
    }
    
    response = requests.post(CLAUDE_API_URL, headers=headers, json=payload, timeout=30)
    
    if response.status_code != 200:
        logger.error(f"Anthropic API error: {response.status_code} - {response.text}")
    
    response.raise_for_status()
    return response.json()["content"][0]["text"]

def try_openrouter(prompt: str) -> str:
    """Try OpenRouter API as fallback"""
    if not settings.OPENROUTER_API_KEY:
        raise RuntimeError("OPENROUTER_API_KEY not set")
    
    logger.info("Attempting chat with OpenRouter...")
    
    headers = {
        "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/hynko431/MedVault",
        "X-Title": "MedVault AI OCR"
    }
    
    payload = {
        "model": settings.OPENROUTER_MODEL,
        "messages": [{"role": "user", "content": prompt}]
    }
    
    response = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers=headers,
        json=payload,
        timeout=30
    )
    
    if response.status_code != 200:
        logger.error(f"OpenRouter API error: {response.status_code} - {response.text}")
    
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]

def try_groq(prompt: str) -> str:
    """Try Groq API as final fallback"""
    if not settings.GROQ_API_KEY:
        raise RuntimeError("GROQ_API_KEY not set")
    
    logger.info("Attempting chat with Groq...")
    
    headers = {
        "Authorization": f"Bearer {settings.GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": settings.GROQ_MODEL,
        "messages": [{"role": "user", "content": prompt}]
    }
    
    response = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers=headers,
        json=payload,
        timeout=30
    )
    
    if response.status_code != 200:
        logger.error(f"Groq API error: {response.status_code} - {response.text}")
    
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]

def medicine_chat(question: str, context: dict | None = None) -> str:
    """
    Chat with AI about medicine-related questions with fallback mechanism.
    
    Fallback chain: Anthropic → OpenRouter → Groq
    
    Args:
        question: User's question about medicines
        context: Optional context dictionary (for future enhancements)
    
    Returns:
        AI-generated response
    
    Raises:
        RuntimeError: If all AI providers fail
    """
    prompt = get_medicine_chat_prompt(question, context)
    errors = []
    
    # 1. Try Anthropic (Primary)
    try:
        return try_anthropic(prompt)
    except Exception as e:
        err = f"Anthropic failed: {str(e)}"
        logger.warning(err)
        errors.append(err)
    
    # 2. Try OpenRouter (Fallback 1)
    try:
        return try_openrouter(prompt)
    except Exception as e:
        err = f"OpenRouter failed: {str(e)}"
        logger.warning(err)
        errors.append(err)
    
    # 3. Try Groq (Fallback 2)
    try:
        return try_groq(prompt)
    except Exception as e:
        err = f"Groq failed: {str(e)}"
        logger.warning(err)
        errors.append(err)
    
    # All providers failed
    error_message = f"All AI providers failed. Errors: {'; '.join(errors)}"
    logger.error(error_message)
    raise RuntimeError(error_message)
