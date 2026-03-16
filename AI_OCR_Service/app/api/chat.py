from fastapi import APIRouter, HTTPException, UploadFile, File, Form, status
from pydantic import BaseModel, Field, field_validator, ConfigDict
from typing import Optional, List, Dict, Any, Protocol, Union, cast
from datetime import datetime, timezone
from enum import Enum
import logging
import base64
import json
import time
import re
import itertools

from app.core.utils.disclaimer import MEDICAL_DISCLAIMER
from app.core.logging.async_logger import log_performance

# Imports
from app.services.chat import enhanced_medicine_chat as emc
from app.services.ocr import ocr_integration as oi
from app.services.utils import medicine_response_formatter as mrf
from app.services.chat.models import ChatContext, MedicineInfo, OCRData, ChatLogger

def _get_enhanced_medicine_chat():
    return emc

def _get_ocr_integration():
    return oi

def _get_medicine_response_formatter():
    return mrf

def get_chat_service():
    emc = _get_enhanced_medicine_chat()
    return emc.get_chat_service()

def get_ocr_service():
    oi = _get_ocr_integration()
    return oi.get_ocr_service()

router = APIRouter()
logger = logging.getLogger(__name__)


# =============================================================================
# Constants
# =============================================================================

class ChatConstants:
    """Constants for chat service configuration."""
    MAX_QUESTION_LENGTH: int = 2000
    MIN_QUESTION_LENGTH: int = 1
    DEFAULT_IMAGE_FORMAT: str = "jpeg"
    SUPPORTED_IMAGE_FORMATS: set[str] = {"jpeg", "jpg", "png", "webp", "gif"}
    MAX_SUGGESTIONS: int = 3
    MAX_CHAT_HISTORY_ITEMS: int = 50


# =============================================================================
# Enums
# =============================================================================

class ProviderType(str, Enum):
    """Available chat provider types."""
    RAG = "rag"
    LEGACY = "legacy"
    FALLBACK = "fallback"
    ANTHROPIC = "Anthropic"
    OPENROUTER = "OpenRouter"
    GROQ = "Groq"
    ERROR = "error"


class ImageFormat(str, Enum):
    """Supported image formats."""
    JPEG = "jpeg"
    JPG = "jpg"
    PNG = "png"
    WEBP = "webp"
    GIF = "gif"


# =============================================================================
# Protocols for type-safe optional imports
# =============================================================================

class MedicineChatRAGProtocol(Protocol):
    """Protocol for RAG chat functions."""
    def __call__(
        self,
        question: str,
        image_data: Optional[str] = None,
        image_format: Optional[str] = None,
        chat_history: Optional[List[Dict[str, str]]] = None,
    ) -> Dict[str, Any]: ...


class KnowledgeBaseProtocol(Protocol):
    """Protocol for knowledge base operations. Flexible to accept varying signatures."""
    def __call__(self, *args: Any, **kwargs: Any) -> Optional[int]: ...


class PrescriptionProcessorProtocol(Protocol):
    """Protocol for prescription processing. Flexible to accept varying signatures."""
    def __call__(self, *args: Any, **kwargs: Any) -> Optional[int]: ...


class LegacyChatProtocol(Protocol):
    """Protocol for legacy chat function."""
    def __call__(self, question: str) -> str: ...


# =============================================================================
# Optional imports with specific error handling
# =============================================================================

def _import_rag_functions() -> tuple[
    Optional[MedicineChatRAGProtocol],
    Optional[KnowledgeBaseProtocol],
    Optional[PrescriptionProcessorProtocol]
]:
    """Import RAG functions with proper error handling."""
    try:
        from app.services.chat.claude_chat_rag import (
            medicine_chat_rag,
            add_to_knowledge_base,
            process_prescription_for_kb,
        )
        return medicine_chat_rag, add_to_knowledge_base, process_prescription_for_kb
    except ImportError as e:
        logger.warning("RAG functions not available: %s", str(e))
        return None, None, None
    except Exception as e:
        logger.error("Unexpected error importing RAG functions: %s", str(e))
        return None, None, None


def _import_legacy_chat() -> Optional[LegacyChatProtocol]:
    """Import legacy chat function with proper error handling."""
    try:
        from app.services.chat.claude_chat import medicine_chat_sync
        return medicine_chat_sync
    except ImportError as e:
        logger.warning("Legacy chat not available: %s", str(e))
        return None
    except Exception as e:
        logger.error("Unexpected error importing legacy chat: %s", str(e))
        return None


# Initialize optional imports at module level to avoid NameError
add_to_knowledge_base: Optional[KnowledgeBaseProtocol] = None
process_prescription_for_kb: Optional[PrescriptionProcessorProtocol] = None

# Removed module-level RAG import and initialization to enable lazy loading
# medicine_chat_rag, add_to_knowledge_base, process_prescription_for_kb = _import_rag_functions()
# medicine_chat = _import_legacy_chat()


# =============================================================================
# Pydantic Models
# =============================================================================

from app.models.schemas import (
    ChatRequest, ChatMetadata, ChatResponse, ImageChatRequest, KnowledgeBaseResponse
)


class MedicineKBEntry(BaseModel):
    """Model for adding a single medicine to knowledge base."""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "T. Numlo-TM (5)",
                "dosage": "1 tab",
                "frequency": "O - X - X -",
                "duration": "Cont.",
                "instructions": "ODPC",
                "form": "tablet"
            }
        }
    )
    
    name: str = Field(..., description="Medicine name")
    dosage: Optional[str] = Field(None, description="Dosage amount and unit")
    frequency: Optional[str] = Field(None, description="How often to take")
    duration: Optional[str] = Field(None, description="How long to take")
    instructions: Optional[str] = Field(None, description="Special instructions")
    form: Optional[str] = Field(None, description="Medicine form (tablet, capsule, etc.)")


class KnowledgeBaseAddRequest(BaseModel):
    """Request model for adding content to knowledge base."""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "content": "Medicine information text",
                "medicines": [
                    {
                        "name": "T. Numlo-TM (5)",
                        "dosage": "1 tab",
                        "frequency": "O - X - X -",
                        "duration": "Cont.",
                        "instructions": "ODPC",
                        "form": "tablet"
                    }
                ],
                "metadata": {"source": "prescription"}
            }
        }
    )
    
    content: Optional[str] = Field(
        None, 
        description="Text content to add to knowledge base (optional if medicines provided)"
    )
    medicines: Optional[List[MedicineKBEntry]] = Field(
        default_factory=list,
        description="List of medicine objects to add to knowledge base"
    )
    metadata: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Additional metadata for the knowledge base entry"
    )



# =============================================================================
# Medicine Response Models
# =============================================================================

class MedicineDetail(BaseModel):
    """Detailed medicine information extracted from prescription/OCR."""
    model_config = ConfigDict(extra='allow')
    
    name: str = Field(..., description="Medicine name")
    dose: Optional[str] = Field(None, description="Dosage amount and unit")
    frequency: Optional[str] = Field(None, description="How often to take (e.g., BD, TID)")
    duration: Optional[str] = Field(None, description="How long to take")
    route: Optional[str] = Field(None, description="Route of administration (oral, injection, etc.)")
    what_it_does: Optional[str] = Field(None, description="Purpose/indication of the medicine")
    side_effects: Optional[List[str]] = Field(default_factory=list, description="Common side effects")
    precautions: Optional[List[str]] = Field(default_factory=list, description="Precautions and warnings")
    how_to_take: Optional[str] = Field(None, description="Instructions on how to take")
    interactions: Optional[List[str]] = Field(default_factory=list, description="Drug interactions")


class FormattedMedicineResponse(BaseModel):
    """Formatted medicine response for display."""
    medicines: List[MedicineDetail] = Field(default_factory=list)
    summary: str = Field(..., description="Formatted text response")
    raw_answer: str = Field(..., description="Original AI answer")


# =============================================================================
# Suggestion Generator
# =============================================================================

class SuggestionEngine:
    """Generates contextual suggestions based on question content."""
    
    # Keyword patterns and their associated suggestions
    SUGGESTION_PATTERNS: Dict[str, List[str]] = {
        "dosage": [
            "What is the recommended duration for this dosage?",
            "Are there any special instructions for taking this medication?",
        ],
        "dose": [
            "What is the recommended duration for this dosage?",
            "What should I do if I miss a dose?",
        ],
        "abbreviation": [
            "What common prescription abbreviations should I know?",
            "Where can I find a guide to medical abbreviations?",
        ],
        "bd": [
            "What does 'BD' (twice daily) mean in prescription terms?",
            "Should BD medications be taken with food?",
        ],
        "od": [
            "What does 'OD' (once daily) mean in prescription terms?",
            "What time of day should I take OD medications?",
        ],
        "tid": [
            "What does 'TID' (three times daily) mean?",
            "How should I space TID medications throughout the day?",
        ],
        "side effect": [
            "What are the most common side effects?",
            "When should I contact a doctor about side effects?",
        ],
        "interaction": [
            "Does this medication interact with alcohol?",
            "What other medications should I avoid?",
        ],
        "pregnancy": [
            "Is this medication safe during pregnancy?",
            "What are the risks during breastfeeding?",
        ],
        "storage": [
            "How should I store this medication?",
            "What is the shelf life of this medication?",
        ],
    }
    
    DEFAULT_SUGGESTIONS: List[str] = [
        "Can you clarify which medicine you mean?",
        "Do you want dosage or side-effect information?",
        "How do I properly store this medication?",
    ]

    @classmethod
    def generate(cls, question: str, answer: str) -> List[str]:
        """Generate contextual suggestions based on question content."""
        if not question:
            limit = int(ChatConstants.MAX_SUGGESTIONS)
            return list(itertools.islice(cls.DEFAULT_SUGGESTIONS, limit))

        question_lower = question.lower()
        suggestions: List[str] = []
        
        # Find matching patterns
        for keyword, suggestion_list in cls.SUGGESTION_PATTERNS.items():
            if keyword in question_lower:
                suggestions.extend(suggestion_list)
                if len(suggestions) >= ChatConstants.MAX_SUGGESTIONS:
                    break
        
        # Add default suggestions if we don't have enough
        if len(suggestions) < ChatConstants.MAX_SUGGESTIONS:
            suggestions.extend(cls.DEFAULT_SUGGESTIONS)
        
        limit = int(ChatConstants.MAX_SUGGESTIONS)
        return list(itertools.islice(suggestions, limit))


# =============================================================================
# Chat Service Handler
# =============================================================================

class ChatServiceHandler:
    """Handles chat service routing between available providers."""
    
    def __init__(self):
        # We will lazy load these to save memory and startup time
        self._rag_available: Optional[bool] = None
        self._legacy_available: Optional[bool] = None
        self.medicine_chat_rag: Optional[MedicineChatRAGProtocol] = None
        self.medicine_chat: Optional[LegacyChatProtocol] = None
        
    def _initialize(self):
        if self._rag_available is None:
            rag_fn, _, _ = _import_rag_functions()
            self.medicine_chat_rag = rag_fn
            self._rag_available = rag_fn is not None
            
        if self._legacy_available is None:
            legacy_fn = _import_legacy_chat()
            self.medicine_chat = legacy_fn
            self._legacy_available = legacy_fn is not None
    
    @property
    def has_available_provider(self) -> bool:
        """Check if any chat provider is available."""
        self._initialize()
        return bool(self._rag_available or self._legacy_available)
    
    def process(
        self,
        question: str,
        image_data: Optional[str] = None,
        image_format: Optional[str] = ChatConstants.DEFAULT_IMAGE_FORMAT,
        chat_history: Optional[List[Dict[str, str]]] = None,
    ) -> tuple[str, ProviderType, float, Optional[str]]:
        """Process chat request using the best available provider.
        
        Returns:
            Tuple of (answer, provider_type, confidence, retrieved_context)
        """
        if not self.has_available_provider:
            raise RuntimeError("No chat provider available")
        
        # Prefer RAG provider
        rag_fn = self.medicine_chat_rag
        if self._rag_available and rag_fn is not None:
            result = rag_fn(
                question=question,
                image_data=image_data,
                image_format=image_format,
                chat_history=chat_history or [],
            )
            
            # Extract values from result with proper typing
            if isinstance(result, dict):
                answer = str(result.get("answer", ""))
                provider_str = str(result.get("provider_used", "rag"))
                provider = ProviderType(provider_str) if provider_str in ProviderType._value2member_map_ else ProviderType.RAG
                confidence = float(result.get("confidence", 0.0))
                retrieved_context_val = result.get("retrieved_context")
                retrieved_context = str(retrieved_context_val) if retrieved_context_val is not None else None
            else:
                answer = str(result)
                provider = ProviderType.RAG
                confidence = 0.0
                retrieved_context = None
            
            from typing import cast
            return cast(tuple[str, ProviderType, float, Optional[str]], (answer, provider, confidence, retrieved_context))
        
        # Fallback to legacy provider
        legacy_fn = self.medicine_chat
        if self._legacy_available and legacy_fn is not None:
            answer = legacy_fn(question)
            return answer, ProviderType.LEGACY, 0.0, None
        
        # Should never reach here due to has_available_provider check
        raise RuntimeError("No chat provider available")


# Initialize service handler
chat_handler = ChatServiceHandler()


# =============================================================================
# Helper Functions for OCR and Medicine Detection
# =============================================================================

def _is_medicine_query(question: str) -> bool:
    """Detect if a query is about medicines."""
    medicine_keywords = [
        'medicine', 'medication', 'drug', 'tablet', 'pill', 'capsule',
        'dose', 'dosage', 'side effect', 'interaction', 'prescription',
        'what does', 'how to take', 'precaution', 'warning', 'contraindication',
        'bd', 'od', 'tid', 'qid', 'sr', 'er', 'mg', 'ml', 'mcg',
        'paracetamol', 'ibuprofen', 'aspirin', 'amoxicillin', 'metformin'
    ]
    question_lower = question.lower()
    return any(keyword in question_lower for keyword in medicine_keywords)


def _extract_medicine_name(question: str) -> Optional[str]:
    """Extract medicine name from a query."""
    # List of common medicines to match
    common_medicines = [
        'paracetamol', 'acetaminophen', 'ibuprofen', 'aspirin', 'amoxicillin',
        'metformin', 'atorvastatin', 'lisinopril', 'amlodipine', 'metoprolol',
        'omeprazole', 'pantoprazole', 'ranitidine', 'cetirizine', 'loratadine',
        'diphenhydramine', 'dextromethorphan', 'guaifenesin', 'pseudoephedrine',
        'phenylephrine', 'codeine', 'tramadol', 'morphine', 'oxycodone',
        'hydrocodone', 'gabapentin', 'pregabalin', 'duloxetine', 'venlafaxine',
        'sertraline', 'fluoxetine', 'escitalopram', 'citalopram', 'paroxetine',
        'bupropion', 'mirtazapine', 'trazodone', 'zolpidem', 'eszopiclone',
        'alprazolam', 'lorazepam', 'clonazepam', 'diazepam', 'temazepam'
    ]
    
    question_lower = question.lower()
    
    # Check for exact matches first
    for med in common_medicines:
        if med in question_lower:
            # Try to capture dose if present (e.g., "Paracetamol 500mg")
            pattern = rf'{med}\s*(\d+\s*(?:mg|ml|mcg|g|iu|units?))?'
            match = re.search(pattern, question_lower)
            if match:
                dose = match.group(1) if match.group(1) else ""
                name = med.capitalize()
                if dose:
                    return f"{name} {dose}"
                return name
    
    # Check for generic patterns like "What is X?"
    patterns = [
        r'what\s+is\s+(\w+)',
        r'what\s+is\s+(\w+\s+\d+\s*(?:mg|ml|mcg|g))',
        r'what\s+are?\s+(?:the\s+)?(?:uses?|side\s+effects?|benefits?)\s+of\s+(\w+)',
        r'how\s+(?:to|do\s+I)\s+take\s+(\w+)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, question_lower)
        if match:
            return match.group(1).capitalize()
    
    return None


async def _fetch_ocr_data(image_url: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Fetch OCR data from the OCR endpoint if image URL is provided."""
    if not image_url:
        return None
    
    try:
        # This would integrate with the /extract OCR endpoint
        # For now, we return None (can be extended when OCR service is available)
        logger.debug("OCR data fetching not yet implemented for URL: %s", image_url)
        return None
    except Exception as e:
        logger.warning("Failed to fetch OCR data: %s", str(e))
        return None


# =============================================================================
# API Endpoints
# =============================================================================

@router.post(
    "/medicine-chat",
    response_model=ChatResponse,
    responses={
        503: {"description": "Service temporarily unavailable"},
        500: {"description": "Internal server error"},
        422: {"description": "Validation error"},
    }
)
@log_performance("Chat Endpoint")
async def chat_endpoint(req: ChatRequest) -> ChatResponse:
    """
    Enhanced medicine chat endpoint with OCR + LLM + RAG integration.
    
    Features:
    - Integrates OCR data with LLM knowledge
    - Provides formatted medicine information (what it does, side effects, precautions, etc.)
    - Supports multi-modal queries (text + images)
    - Uses RAG for knowledge base context
    - LangChain-powered enrichment
    - Comprehensive logging throughout
    - Medical disclaimer included
    
    Example response:
    ```
    user: "What is Paracetamol 500mg?"
    
    AI Response:
    Medicine: Paracetamol 500mg
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━
    
    📋 What it does:
    Reduces fever and relieves mild to moderate pain...
    
    ⚠️ Common Side Effects:
    - Nausea (rare)
    - Allergic reactions (very rare)
    ...
    ```
    """
    start_time = time.time()
    enhanced_chat_service = get_chat_service()
    ocr_service = get_ocr_service()
    
    try:
        req_question = str(req.question)
        question_display = "".join(itertools.islice(req_question, 50))
        logger.info(f"🔄 Processing chat request: {question_display}...")
        ChatLogger.log_chat_request(
            req_question,
            has_image=bool(req.image_base64),
            ocr_data_available=bool(req.image_base64)
        )
        
        has_image = bool(req.image_base64)
        is_medicine_query = _is_medicine_query(req.question)
        
        # Step 1: Extract OCR data if image is provided
        ocr_data = None
        prescription_medicines = []
        
        if req.image_base64:
            try:
                logger.debug("📸 Extracting OCR data from image...")
                oi = _get_ocr_integration()
                ocr_text = await oi.OCRIntegrationService.extract_ocr_from_image(req.image_base64)
                
                if ocr_text:
                    logger.info(f"✅ OCR extraction successful: {len(ocr_text)} chars")
                    
                    # Parse medicines from OCR
                    ocr_data = enhanced_chat_service.process_ocr_data(ocr_text)
                    prescription_medicines = ocr_data.medicines
                    
                    logger.info(f"📋 Found {len(prescription_medicines)} medicines in prescription")
                    for med in prescription_medicines:
                        ChatLogger.log_ocr_extraction(med.name, {
                            "dose": med.dose,
                            "frequency": med.frequency,
                            "route": med.route
                        })
            
            except Exception as e:
                logger.warning(f"⚠️ OCR extraction failed: {str(e)}")
                ChatLogger.log_error("OCR_EXTRACTION", e)
                # Continue without OCR data
        
        # Step 2: Enrich medicines with LLM knowledge
        enriched_medicines = []
        if prescription_medicines and is_medicine_query:
            try:
                logger.debug(f"🧠 Enriching {len(prescription_medicines)} medicines with LLM...")
                for medicine in prescription_medicines:
                    enriched = enhanced_chat_service.enrich_with_llm(medicine)
                    enriched_medicines.append(enriched)
                logger.info(f"✅ Enriched {len(enriched_medicines)} medicines")
            except Exception as e:
                logger.warning(f"⚠️ LLM enrichment failed: {str(e)}")
                ChatLogger.log_error("LLM_ENRICHMENT", e)
                enriched_medicines = prescription_medicines
        
        # Step 3: Build context for LLM
        context = ChatContext(
            question=req.question,
            ocr_data=ocr_data,
            chat_history=req.chat_history or [],
            current_medicines=enriched_medicines or prescription_medicines,
        )
        
        # Step 4: Get LLM answer
        logger.debug("💬 Getting LLM response...")
        
        # Initialize default metadata values
        provider = ProviderType.RAG
        confidence = 0.85
        retrieved_context = getattr(context.ocr_data, 'raw_text', None) if context.ocr_data else None
        llm_answer = "I'm sorry, I couldn't process your request at this time."  # Initialized to prevent UnboundLocalError
        
        if is_medicine_query and context.current_medicines:
            llm_answer, provider_name = enhanced_chat_service.answer_medicine_query(context)
            try:
                # Attempt to parse the provider name from the enhanced chat service
                provider = ProviderType(provider_name)
            except ValueError:
                provider = ProviderType.FALLBACK
        else:
            # For non-medicine queries or if no medicines found, use regular RAG chat
            logger.debug("Using RAG chat provider for general query...")
            img_format = req.image_format or "jpeg"
            res_answer, res_provider, res_confidence, res_context = chat_handler.process(
                question=req.question,
                image_data=req.image_base64,
                image_format=img_format,
                chat_history=req.chat_history,
            )
            llm_answer = res_answer
            provider = res_provider
            confidence = res_confidence
            retrieved_context = res_context
        
        # Step 5: Format response
        logger.debug("🎨 Formatting response...")
        
        # Build final response - for medicine queries, show structured format
        if is_medicine_query:
            # If we have medicines from OCR, use them; otherwise extract from query
            if enriched_medicines or prescription_medicines:
                medicines_to_format = enriched_medicines if enriched_medicines else prescription_medicines
                mrf = _get_medicine_response_formatter()
                final_answer = mrf.MedicineResponseFormatter.format_multiple_medicines(medicines_to_format)
            else:
                # No OCR data - create medicine from query and enrich it
                logger.debug("Creating medicine info from query...")
                medicine_name = _extract_medicine_name(req.question)
                if medicine_name:
                    # Create MedicineInfo with all required fields
                    med_info = MedicineInfo(
                        name=medicine_name,
                        dose=None,
                        frequency=None,
                        duration=None,
                        route=None,
                        what_it_does=None,
                        side_effects=[],
                        precautions=[],
                        how_to_take=None,
                        interactions=[],
                        source="query"
                    )
                    try:
                        enriched = enhanced_chat_service.enrich_with_llm(med_info)
                        mrf = _get_medicine_response_formatter()
                        final_answer = mrf.MedicineResponseFormatter.format_single_medicine(enriched)
                    except Exception as e:
                        logger.warning(f"Failed to enrich medicine: {e}")
                        final_answer = llm_answer
                else:
                    final_answer = llm_answer
        else:
            # Non-medicine queries: show LLM answer
            final_answer = llm_answer
        
        # Add disclaimer
        if MEDICAL_DISCLAIMER:
            final_answer = f"{final_answer}\n\n---\n{MEDICAL_DISCLAIMER}"
        
        # Generate suggestions
        suggestions = SuggestionEngine.generate(req.question, llm_answer)
        
        # Calculate processing time
        processing_time_ms = int((time.time() - start_time) * 1000)
        
        logger.info(f"✅ Response ready: {processing_time_ms}ms")
        ChatLogger.log_chat_response(
            processing_time_ms,
            len(enriched_medicines),
            "enhanced_rag"
        )
        
        # Use dict-based construction for Pydantic models to satisfy Pyre2
        return ChatResponse(**response_data) # type: ignore

    except ValueError as e:
        logger.warning(f"❌ Validation error: {str(e)}")
        ChatLogger.log_error("VALIDATION", e)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"error": "Validation error", "message": str(e)}
        )
    except RuntimeError as e:
        logger.error(f"❌ Service unavailable: {str(e)}")
        ChatLogger.log_error("SERVICE", e)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"error": "Service unavailable", "message": str(e)}
        )
    except Exception as e:
        logger.exception(f"❌ Unexpected error in chat endpoint")
        ChatLogger.log_error("CHAT_ENDPOINT", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "Internal server error",
                "message": "An unexpected error occurred",
                "technical_details": str(e)
            }
        )


@router.post(
    "/medicine-chat/upload",
    response_model=ChatResponse,
    responses={
        503: {"description": "Service temporarily unavailable"},
        500: {"description": "Internal server error"},
        422: {"description": "Validation error"},
    }
)
async def chat_with_file_upload(
    question: str = Form(..., min_length=1, max_length=ChatConstants.MAX_QUESTION_LENGTH),
    image: Optional[UploadFile] = File(None),
    chat_history: str = Form("[]"),
    include_context: bool = Form(True),
) -> ChatResponse:
    """
    File upload endpoint for medicine chat with OCR extraction.
    
    Features:
    - Accepts prescription images (JPEG, PNG, WebP, GIF)
    - Automatically extracts text via OCR
    - Processes medicine information from prescription
    - Enriches data with LLM knowledge
    - Provides formatted medicine details
    
    Args:
        question: User's question about the prescription/medicines
        image: Prescription image file
        chat_history: Previous chat messages as JSON array
        include_context: Whether to include OCR context in response
        
    Returns:
        Formatted medicine information with answer and suggestions
    """
    start_time = time.time()
    enhanced_chat_service = get_chat_service()
    ocr_service = get_ocr_service()
    
    try:
        upload_question = str(question)
        upload_display = "".join(itertools.islice(upload_question, 50))
        logger.info(f"🔄 Processing file upload: question='{upload_display}...'")
        
        # Parse chat history
        parsed_history: List[Dict[str, str]] = []
        if chat_history and chat_history.strip():
            try:
                parsed_data = json.loads(chat_history)
                if isinstance(parsed_data, list):
                    limit = int(ChatConstants.MAX_CHAT_HISTORY_ITEMS)
                    parsed_history = list(itertools.islice(parsed_data, limit))
                    logger.debug(f"Parsed chat history: {len(parsed_history)} items")
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse chat history JSON: {str(e)}")
        
        # Process image upload
        image_b64: Optional[str] = None
        image_format = ChatConstants.DEFAULT_IMAGE_FORMAT
        ocr_extracted_text: Optional[str] = None
        prescription_medicines = []
        
        if image is not None:
            logger.debug(f"📸 Processing uploaded image: {image.filename}")
            
            # Validate file size (max 10MB)
            body = await image.read()
            if len(body) > 10 * 1024 * 1024:  # type: ignore[arg-type]
                logger.error("Image file too large")
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail="Image file too large. Maximum size is 10MB."
                )
            
            # Encode to base64
            image_b64 = base64.b64encode(body).decode("utf-8")
            logger.debug(f"Image encoded to base64: {len(image_b64)} chars")
            
            # Infer format from filename or content type
            filename = image.filename or ""
            content_type = image.content_type or ""
            
            if filename and "." in filename:
                ext = filename.rsplit(".", 1)[-1].lower()
                if ext in ChatConstants.SUPPORTED_IMAGE_FORMATS:
                    image_format = ext
                    logger.debug(f"Detected image format from filename: {image_format}")
            
            elif content_type:
                format_from_ct = content_type.split("/")[-1].lower()
                if format_from_ct in ChatConstants.SUPPORTED_IMAGE_FORMATS:
                    image_format = format_from_ct
                    logger.debug(f"Detected image format from content-type: {image_format}")
            
            # Extract OCR from image
            try:
                logger.debug("🔄 Starting OCR extraction...")
                oi = _get_ocr_integration()
                ocr_extracted_text = await oi.OCRIntegrationService.extract_ocr_from_image(image_b64)
                
                if ocr_extracted_text:
                    logger.info(f"✅ OCR extraction successful: {len(ocr_extracted_text)} chars")
                    
                    # Parse medicines from OCR
                    ocr_parsed = oi.OCRIntegrationService.parse_ocr_for_medicines(ocr_extracted_text)
                    prescription_medicines = ocr_parsed.get("medicines", [])
                    logger.info(f"📋 Found {len(prescription_medicines)} medicines in OCR")
                    
                    # Enrich with LLM
                    if prescription_medicines:
                        try:
                            logger.debug("🧠 Enriching medicines with LLM...")
                            enriched_medicines = []
                            for med in prescription_medicines:
                                # Convert dict to MedicineInfo if needed
                                if isinstance(med, dict):
                                    med_info = MedicineInfo(**med)
                                else:
                                    med_info = med
                                
                                enriched = enhanced_chat_service.enrich_with_llm(med_info)
                                enriched_medicines.append(enriched)
                            
                            prescription_medicines = enriched_medicines
                            logger.info(f"✅ Enriched {len(prescription_medicines)} medicines")
                        except Exception as e:
                            logger.warning(f"⚠️ LLM enrichment failed: {str(e)}")
                            ChatLogger.log_error("LLM_ENRICHMENT", e)
                
                else:
                    logger.warning("⚠️ OCR extraction returned empty text")
            
            except Exception as e:
                logger.warning(f"⚠️ OCR processing failed: {str(e)}")
                ChatLogger.log_error("OCR_PROCESSING", e)
        
        # Create ChatRequest and process
        req = ChatRequest(
            question=question,
            image_base64=image_b64,
            image_format=image_format,
            chat_history=parsed_history,
            include_context=include_context,
        )
        
        logger.debug("📤 Forwarding to main chat endpoint...")
        
        # Process through enhanced chat
        is_medicine_query = _is_medicine_query(question)
        
        # Build context with OCR data properly included
        # Convert prescription_medicines to MedicineInfo objects
        current_medicines_list = []
        if prescription_medicines:
            for m in prescription_medicines:
                if isinstance(m, MedicineInfo):
                    current_medicines_list.append(m)
                elif isinstance(m, dict):
                    current_medicines_list.append(MedicineInfo(**m))
                else:
                    # Handle case where m might be a string or other type
                    logger.warning(f"Unexpected medicine type: {type(m)}, value: {m}")
        
        # Create OCRData with the extracted text and parsed medicines
        ocr_data_obj = None
        if ocr_extracted_text:
            ocr_data_obj = OCRData(
                raw_text=ocr_extracted_text,
                medicines=current_medicines_list,
                extraction_confidence=0.85 if current_medicines_list else 0.5,
                extraction_timestamp=datetime.utcnow().isoformat()
            )
            logger.info(f"📄 OCR data created with {len(ocr_extracted_text)} chars and {len(current_medicines_list)} medicines")
        else:
            logger.warning("⚠️ No OCR text available for context")
        
        context = ChatContext(
            question=question,
            ocr_data=ocr_data_obj,  # FIXED: Now includes actual OCR data
            chat_history=parsed_history,
            current_medicines=current_medicines_list,
        )
        
        # Get LLM response
        logger.debug("💬 Getting enhanced response...")
        llm_answer, provider_name = enhanced_chat_service.answer_medicine_query(context)
        
        # Format response
        formatted_answer = llm_answer
        if is_medicine_query and prescription_medicines:
            try:
                # Convert to MedicineInfo objects if needed
                med_objects = []
                for m in prescription_medicines:
                    if isinstance(m, MedicineInfo):
                        med_objects.append(m)
                    elif isinstance(m, dict):
                        med_objects.append(MedicineInfo(**m))
                
                mrf = _get_medicine_response_formatter()
                formatted_answer = mrf.MedicineResponseFormatter.format_multiple_medicines(med_objects)
            except Exception as e:
                logger.warning(f"Medicine formatting failed: {str(e)}")
        
        # Build final response
        mrf = _get_medicine_response_formatter()
        final_answer = mrf.ResponseBuilder.build_medicine_query_response(
            llm_answer=llm_answer,
            medicines=prescription_medicines if isinstance(prescription_medicines, list) and 
                    prescription_medicines and isinstance(prescription_medicines[0], MedicineInfo)
                    else None,
            include_disclaimer=True,
            disclaimer_text=MEDICAL_DISCLAIMER
        )
        
        # Generate suggestions
        suggestions = SuggestionEngine.generate(question, llm_answer)
        
        # Calculate processing time
        processing_time_ms = int((time.time() - start_time) * 1000)
        
        logger.info(f"✅ Upload chat complete: {processing_time_ms}ms")
        
        return ChatResponse(
            status="success",
            answer=final_answer,
            disclaimer=MEDICAL_DISCLAIMER,
            metadata=ChatMetadata(
                provider_used=ProviderType.RAG.value, # Changed to .value to match str type
                confidence=0.85 if ocr_extracted_text else 0.7,
                has_image=image is not None,
                processing_time_ms=processing_time_ms,
            ),
            retrieved_context=ocr_extracted_text,
            suggestions=suggestions,
            error_details=None,
        )


    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Upload chat failed")
        ChatLogger.log_error("UPLOAD_CHAT", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "Upload processing failed", "message": str(e)}
        )


@router.post(
    "/knowledge-base/add",
    response_model=KnowledgeBaseResponse,
    responses={
        501: {"description": "Knowledge base functionality not installed"},
        500: {"description": "Internal server error"},
        422: {"description": "Validation error - Invalid request format"},
    }
)
async def add_to_knowledge_base_endpoint(request: KnowledgeBaseAddRequest) -> KnowledgeBaseResponse:
    """
    Add content to knowledge base (if KB helper available).
    
    Supports:
    - Text content directly via `content` field
    - Structured medicine data via `medicines` array
    - Metadata for categorization
    
    Example requests:
    
    **Single medicine:**
    ```json
    {
        "medicines": [
            {
                "name": "T. Numlo-TM (5)",
                "dosage": "1 tab",
                "frequency": "O - X - X -",
                "duration": "Cont.",
                "instructions": "ODPC",
                "form": "tablet"
            }
        ]
    }
    ```
    
    **Text content:**
    ```json
    {
        "content": "Medicine information text",
        "metadata": {"source": "manual"}
    }
    ```
    """
    if add_to_knowledge_base is None:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Knowledge base functionality not installed"
        )
    
    # Build content from medicines if provided
    content = request.content
    medicines = request.medicines or []
    if not content and medicines:
        # Convert medicine objects to formatted text
        medicine_texts: List[str] = []
        for med in medicines:
            med_lines = [f"Medicine: {med.name}"]
            if med.dosage:
                med_lines.append(f"Dosage: {med.dosage}")
            if med.frequency:
                med_lines.append(f"Frequency: {med.frequency}")
            if med.duration:
                med_lines.append(f"Duration: {med.duration}")
            if med.instructions:
                med_lines.append(f"Instructions: {med.instructions}")
            if med.form:
                med_lines.append(f"Form: {med.form}")
            medicine_texts.append(str(" | ".join(med_lines)))
        content = "\n".join(medicine_texts)
    
    if not content:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Either 'content' or 'medicines' must be provided"
        )
    
    # Merge metadata
    metadata = request.metadata or {}
    if medicines:
        metadata["type"] = "medicine"
        metadata["medicine_count"] = len(medicines)
        metadata["medicine_names"] = [m.name for m in medicines]
    
    try:
        added = add_to_knowledge_base(content, metadata=metadata)
        logger.info(f"✅ Added {added} document(s) to knowledge base")
        return KnowledgeBaseResponse(
            message=str(f"Added {added} document(s) to knowledge base"),
            documents_added=added or 0,
            status="success"
        )
    except Exception as e:
        logger.exception("KB add failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post(
    "/knowledge-base/add-prescription",
    response_model=KnowledgeBaseResponse,
    responses={
        501: {"description": "Prescription KB processing not available"},
        500: {"description": "Internal server error"},
    }
)
async def add_prescription_to_kb(prescription_data: Dict[str, Any]) -> KnowledgeBaseResponse:
    """Add prescription data to knowledge base for RAG retrieval."""
    if process_prescription_for_kb is None:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Prescription KB processing not available"
        )
    
    if not isinstance(prescription_data, dict):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Prescription data must be a dictionary"
        )
    
    try:
        count = process_prescription_for_kb(prescription_data)
        return KnowledgeBaseResponse(
            message="Prescription added",
            documents_added=count or 0,
            status="success"
        )
    except Exception as e:
        logger.exception("Prescription KB add failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
