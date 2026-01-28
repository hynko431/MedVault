from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.services.claude_chat import medicine_chat
import logging
from app.core.disclaimer import MEDICAL_DISCLAIMER

router = APIRouter()
logger = logging.getLogger(__name__)

class ChatRequest(BaseModel):
    question: str

@router.post("/medicine-chat")
def chat_endpoint(req: ChatRequest):
    """
    Chat endpoint for medicine-related questions with AI fallback mechanism.
    
    Fallback chain: Anthropic → OpenRouter → Groq
    
    Returns:
        - answer: AI-generated response
        - disclaimer: Medical disclaimer
        - provider_used: Which AI provider was used (for transparency)
    """
    try:
        answer = medicine_chat(req.question)
        return {
            "answer": answer,
            "disclaimer": MEDICAL_DISCLAIMER,
            "status": "success"
        }
    except RuntimeError as e:
        logger.error(f"Chat service failed: {str(e)}")
        raise HTTPException(
            status_code=503,
            detail={
                "error": "Service temporarily unavailable",
                "message": "All AI providers are currently unavailable. Please try again later.",
                "technical_details": str(e),
            },
        ) from e
    except Exception as e:
        logger.error(f"Unexpected error in chat endpoint: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Internal server error",
                "message": "An unexpected error occurred while processing your request.",
            },
        ) from e
