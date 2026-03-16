"""
Chat Service Models

Data models for chat functionality including medicine information,
OCR data, chat context, and logging.
"""

from typing import Optional, List, Dict, Any, cast
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import logging
import itertools

from app.core.logging.logger import get_logger

logger = get_logger("chat_models")


class MessageRole(str, Enum):
    """Message roles in chat conversations."""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


@dataclass
class MedicineInfo:
    """
    Structured medicine information extracted from prescriptions
    or created from user queries.
    """
    name: str
    dose: Optional[str] = None
    frequency: Optional[str] = None
    duration: Optional[str] = None
    route: Optional[str] = None
    what_it_does: Optional[str] = None
    side_effects: List[str] = field(default_factory=list)
    precautions: List[str] = field(default_factory=list)
    how_to_take: Optional[str] = None
    interactions: List[str] = field(default_factory=list)
    source: str = "unknown"  # "ocr", "llm", "query", "knowledge_base"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "dose": self.dose,
            "frequency": self.frequency,
            "duration": self.duration,
            "route": self.route,
            "what_it_does": self.what_it_does,
            "side_effects": self.side_effects,
            "precautions": self.precautions,
            "how_to_take": self.how_to_take,
            "interactions": self.interactions,
            "source": self.source,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MedicineInfo":
        """Create from dictionary."""
        return cls(
            name=data.get("name", "Unknown"),
            dose=data.get("dose"),
            frequency=data.get("frequency"),
            duration=data.get("duration"),
            route=data.get("route"),
            what_it_does=data.get("what_it_does"),
            side_effects=data.get("side_effects", []),
            precautions=data.get("precautions", []),
            how_to_take=data.get("how_to_take"),
            interactions=data.get("interactions", []),
            source=data.get("source", "unknown"),
        )


@dataclass
class OCRData:
    """
    OCR-extracted data from prescription images.
    Contains raw text and parsed medicine information.
    """
    raw_text: str
    medicines: List[MedicineInfo] = field(default_factory=list)
    extraction_confidence: float = 0.0
    extraction_timestamp: Optional[str] = None
    image_metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        if self.extraction_timestamp is None:
            self.extraction_timestamp = datetime.now(timezone.utc).isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "raw_text": self.raw_text,
            "medicines": [m.to_dict() for m in self.medicines],
            "extraction_confidence": self.extraction_confidence,
            "extraction_timestamp": self.extraction_timestamp,
            "image_metadata": self.image_metadata,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "OCRData":
        """Create from dictionary."""
        medicines_raw = data.get("medicines", [])
        medicines = [
            MedicineInfo.from_dict(m) if isinstance(m, dict) else cast(MedicineInfo, m)
            for m in medicines_raw
        ]
        return cls(
            raw_text=data.get("raw_text", ""),
            medicines=medicines,
            extraction_confidence=data.get("extraction_confidence", 0.0),
            extraction_timestamp=data.get("extraction_timestamp"),
            image_metadata=data.get("image_metadata", {}),
        )


@dataclass
class ChatMessage:
    """
    Single chat message in a conversation.
    """
    role: MessageRole
    content: str
    timestamp: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now(timezone.utc).isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "role": self.role.value,
            "content": self.content,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ChatMessage":
        """Create from dictionary."""
        # Explicitly cast to MessageRole enum (defined at top of this file)
        role_str = str(data.get("role", "user")).lower()
        role: MessageRole = cast(MessageRole, MessageRole(role_str))
        return cls(
            role=role,
            content=data.get("content", ""),
            timestamp=data.get("timestamp"),
            metadata=data.get("metadata", {}),
        )


@dataclass
class ChatContext:
    """
    Context for a chat interaction including question,
    OCR data, chat history, and current medicines.
    """
    question: str
    ocr_data: Optional[OCRData] = None
    chat_history: List[Dict[str, str]] = field(default_factory=list)
    current_medicines: List[MedicineInfo] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        ocr = self.ocr_data
        return {
            "question": self.question,
            "ocr_data": ocr.to_dict() if ocr is not None else {},
            "chat_history": self.chat_history,
            "current_medicines": [m.to_dict() for m in self.current_medicines],
            "metadata": self.metadata,
        }
    
    def get_medicine_names(self) -> List[str]:
        """Get list of medicine names from context."""
        names = [m.name for m in self.current_medicines if m.name]
        ocr = self.ocr_data
        if ocr is not None:
            names.extend([m.name for m in ocr.medicines if m.name])
        return list(set(names))


@dataclass
class EnrichedMedicineResponse:
    """
    Response containing enriched medicine information.
    """
    medicine: MedicineInfo
    enrichment_source: str = "llm"  # "llm", "knowledge_base", "hybrid"
    confidence: float = 0.0
    processing_time_ms: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "medicine": self.medicine.to_dict(),
            "enrichment_source": self.enrichment_source,
            "confidence": self.confidence,
            "processing_time_ms": self.processing_time_ms,
            "metadata": self.metadata,
        }


class ChatLogger:
    """
    Logger for chat interactions and events.
    """
    
    @staticmethod
    def log_chat_request(
        question: str,
        has_image: bool = False,
        ocr_data_available: bool = False,
        user_id: Optional[str] = None
    ) -> None:
        """Log a chat request."""
        # Fix slicing diagnostic using islice
        preview = "".join(itertools.islice(question, 50))
        logger.info(
            f"Chat request: question='{preview}...', "
            f"has_image={has_image}, "
            f"ocr_data_available={ocr_data_available}"
        )
    
    @staticmethod
    def log_chat_response(
        processing_time_ms: int,
        medicines_count: int,
        provider: str = "unknown"
    ) -> None:
        """Log a chat response."""
        logger.info(
            f"Chat response: time={processing_time_ms}ms, "
            f"medicines={medicines_count}, "
            f"provider={provider}"
        )
    
    @staticmethod
    def log_ocr_extraction(
        medicine_name: str,
        details: Dict[str, Any]
    ) -> None:
        """Log OCR extraction of a medicine."""
        logger.info(f"OCR extracted: {medicine_name} - {details}")
    
    @staticmethod
    def log_llm_enrichment(
        medicine_name: str,
        enriched_fields: List[str]
    ) -> None:
        """Log LLM enrichment of a medicine."""
        logger.info(f"LLM enriched: {medicine_name} - fields={enriched_fields}")
    
    @staticmethod
    def log_error(
        error_type: str,
        error: Exception,
        context: Optional[Dict[str, Any]] = None
    ) -> None:
        """Log a chat-related error."""
        logger.error(
            f"Chat error [{error_type}]: {str(error)}",
            exc_info=True,
            extra={"context": context}
        )


@dataclass
class ChatSession:
    """
    Chat session containing full conversation history.
    """
    session_id: str
    messages: List[ChatMessage] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def add_message(self, role: MessageRole, content: str, **metadata) -> ChatMessage:
        """Add a message to the session."""
        message = ChatMessage(
            role=role,
            content=content,
            metadata=metadata
        )
        self.messages.append(message)
        # Use timezone-aware utcnow
        self.updated_at = datetime.now(timezone.utc)
        return message
    
    def get_history(self, limit: int = 50) -> List[Dict[str, str]]:
        """Get chat history as list of dicts."""
        msgs = self.messages
        if limit > 0:
            start_idx = max(0, len(msgs) - limit)
            messages = list(itertools.islice(msgs, start_idx, None))
        else:
            messages = msgs
        return [
            {"role": str(m.role.value), "content": str(m.content)}
            for m in messages
        ]
    
    def clear_history(self) -> None:
        """Clear chat history."""
        self.messages.clear()
        self.updated_at = datetime.now(timezone.utc)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "session_id": self.session_id,
            "messages": [m.to_dict() for m in self.messages],
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "metadata": self.metadata,
        }


@dataclass
class KnowledgeBaseDocument:
    """
    Document stored in the knowledge base for RAG retrieval.
    """
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    embedding: Optional[List[float]] = None
    document_id: Optional[str] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    def __post_init__(self):
        if self.document_id is None:
            import hashlib
            data_to_hash = f"{self.content}{self.created_at.isoformat()}"
            full_hash = hashlib.sha256(data_to_hash.encode()).hexdigest()
            self.document_id = "".join(itertools.islice(full_hash, 16))
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "document_id": self.document_id,
            "content": self.content,
            "metadata": self.metadata,
            "embedding": self.embedding,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class RAGRetrievalResult:
    """
    Result from RAG retrieval.
    """
    documents: List[KnowledgeBaseDocument]
    query: str
    retrieval_time_ms: float
    total_documents_found: int
    
    def to_context_string(self, max_docs: int = 3) -> str:
        """Convert retrieved documents to context string for LLM."""
        context_parts = []
        all_docs = self.documents
        docs = list(itertools.islice(all_docs, max_docs))
        for i, doc in enumerate(docs, 1):
            context_parts.append(f"[Document {i}]\n{doc.content}\n")
        return "\n\n".join(context_parts)