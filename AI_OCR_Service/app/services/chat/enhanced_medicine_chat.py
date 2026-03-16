"""
Enhanced Medicine Chat Service with LangChain/LangGraph Integration
- Integrates OCR data with LLM knowledge
- Uses LangGraph for structured workflows
- Provides medicine information formatting
- Comprehensive logging throughout
"""

import os
import logging
import json
from typing import Optional, List, Dict, Any, Union
from datetime import datetime, timezone
from abc import ABC, abstractmethod

from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from pydantic import BaseModel, Field

from app.services.chat.models import ChatLogger, MedicineInfo, OCRData, ChatContext, EnrichedMedicineResponse
from app.core.logging.async_logger import log_performance

try:
    from langfuse.callback import CallbackHandler
    langfuse_handler = CallbackHandler()
except Exception:
    langfuse_handler = None

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)





# =============================================================================
# LLM Prompt Templates
# =============================================================================

class MedicinePrompts:
    """Structured prompts for medicine information extraction."""
    
    MEDICINE_ENRICHMENT_PROMPT = """
    You are a medical information specialist. Based on the prescription/OCR data and your knowledge,
    provide enriched medicine information.
    
    Medicine from prescription: {medicine_name}
    Dose from OCR: {ocr_dose}
    Frequency from OCR: {ocr_frequency}
    
    Please provide:
    1. What it does (indication/purpose) - 1-2 sentences
    2. Common side effects - list 3-5
    3. Precautions/warnings - list 3-5
    4. How to take - 1-2 sentences
    5. Drug interactions - mention common ones if any
    
    Format your response as JSON with these exact keys:
    {{
        "what_it_does": "...",
        "side_effects": ["...", "..."],
        "precautions": ["...", "..."],
        "how_to_take": "...",
        "interactions": ["..."]
    }}
    """
    
    MEDICINE_QUERY_RESPONSE_PROMPT = """
    You are a medical information assistant. Help answer the user's question about medicine
    using both OCR data and your knowledge.
    
    User Question: {question}
    
    Available Medicine Data:
    {medicine_data}
    
    Prescription/OCR Data:
    {ocr_context}
    
    User's Current Medicines:
    {current_medicines}
    
    Please provide:
    1. Clear answer to the user's question
    2. Relevant information from their prescription/OCR data
    3. Additional helpful context from your knowledge
    4. Any important warnings or precautions
    
    Always include a medical disclaimer.
    """
    
    @staticmethod
    def get_enrichment_prompt(medicine_name: str, ocr_dose: Optional[str] = None, 
                            ocr_frequency: Optional[str] = None) -> str:
        """Get medicine enrichment prompt."""
        logger.debug(f"Generating enrichment prompt for: {medicine_name}")
        return MedicinePrompts.MEDICINE_ENRICHMENT_PROMPT.format(
            medicine_name=medicine_name,
            ocr_dose=ocr_dose or "Not specified",
            ocr_frequency=ocr_frequency or "Not specified"
        )
    
    @staticmethod
    def get_query_response_prompt(question: str, medicines_data: str, 
                                  ocr_context: str, current_meds: str) -> str:
        """Get medicine query response prompt."""
        logger.debug(f"Generating response prompt for question: {question[:50]}...")  # type: ignore[index]
        return MedicinePrompts.MEDICINE_QUERY_RESPONSE_PROMPT.format(
            question=question,
            medicine_data=medicines_data,
            ocr_context=ocr_context,
            current_medicines=current_meds
        )


# =============================================================================
# Chat Service Components
# =============================================================================

class LLMProvider(ABC):
    """Abstract base for LLM providers."""
    
    @abstractmethod
    def enrich_medicine_info(self, medicine_name: str, ocr_dose: Optional[str] = None,
                           ocr_frequency: Optional[str] = None) -> Dict[str, Any]:
        """Enrich medicine information from OCR data."""
        ...
    
    @abstractmethod
    def answer_medicine_query(self, question: str, context: ChatContext) -> str:
        """Answer user's medicine question with context."""
        ...


class AnthropicLLMProvider(LLMProvider):
    """Claude-based LLM provider using LangChain."""
    llm: Any = None  # Set in __init__; typed Any to accept ChatAnthropic or None
    
    def __init__(self):
        """Initialize Anthropic provider."""
        try:
            from langchain_anthropic import ChatAnthropic
            from pydantic import SecretStr
            from app.core.config.config import settings
            
            if not settings.ANTHROPIC_API_KEY:
                logger.warning("⚠️ ANTHROPIC_API_KEY not set")
                self.llm = None
                return
            
            self.llm = ChatAnthropic(
                model_name="claude-3-5-sonnet-20241022",
                api_key=SecretStr(settings.ANTHROPIC_API_KEY),
                temperature=0.3,  # Lower temp for consistent medical info
                timeout=30,
            ) # type: ignore
            logger.info("✅ Anthropic Claude LLM provider initialized")
        except Exception as e:
            ChatLogger.log_error("LLM_INIT", e)
            self.llm = None
    
    def enrich_medicine_info(self, medicine_name: str, ocr_dose: Optional[str] = None,
                           ocr_frequency: Optional[str] = None) -> Dict[str, Any]:
        """Enrich medicine information using Claude."""
        if not self.llm:
            logger.warning(f"Anthropic LLM not available, returning empty enrichment for {medicine_name}")
            return {}
        
        try:
            prompt = MedicinePrompts.get_enrichment_prompt(medicine_name, ocr_dose, ocr_frequency)
            
            logger.debug(f"Sending enrichment request to Anthropic for: {medicine_name}")
            response = self.llm.invoke(prompt, config={"callbacks": [langfuse_handler]} if langfuse_handler else None)
            
            # Handle response content safely
            if isinstance(response, str):
                content = response
            elif hasattr(response, 'content'):
                content = response.content if isinstance(response.content, str) else str(response.content)
            else:
                content = str(response)
            
            logger.debug(f"Anthropic Response: {content[:100]}...")  # type: ignore[index]
            
            # Extract JSON from response
            import re
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                enriched = json.loads(json_match.group())
                ChatLogger.log_llm_enrichment(medicine_name, list(enriched.keys()))
                return enriched
            else:
                logger.warning(f"No JSON found in Anthropic response for {medicine_name}")
                return {}
        
        except Exception as e:
            ChatLogger.log_error("ANTHROPIC_MEDICINE_ENRICHMENT", e)
            return {}
    
    def answer_medicine_query(self, question: str, context: ChatContext) -> str:
        """Answer medicine query using Claude with context."""
        if not self.llm:
            logger.warning("Anthropic LLM not available, cannot answer query")
            return "Service temporarily unavailable. Please try again later."
        
        try:
            # Prepare context strings
            medicines_data = self._format_medicines(context.ocr_data.medicines if context.ocr_data else [])
            ocr_context = self._format_ocr_data(context.ocr_data)
            current_meds = self._format_medicines(context.current_medicines)
            
            prompt = MedicinePrompts.get_query_response_prompt(
                question, medicines_data, ocr_context, current_meds
            )
            
            logger.debug(f"Sending query to Anthropic: {question[:50]}...")  # type: ignore[index]
            response = self.llm.invoke(prompt, config={"callbacks": [langfuse_handler]} if langfuse_handler else None)
            
            # Handle response content
            if isinstance(response, str):
                answer = response
            elif hasattr(response, 'content'):
                answer = response.content if isinstance(response.content, str) else str(response.content)
            else:
                answer = str(response)
            
            logger.debug(f"Anthropic Answer generated: {len(answer)} characters")
            return answer
        
        except Exception as e:
            ChatLogger.log_error("ANTHROPIC_QUERY_RESPONSE", e)
            return "Unable to process your query at this moment. Please try again."
    
    @staticmethod
    def _format_medicines(medicines: List[MedicineInfo]) -> str:
        """Format medicines list for LLM context."""
        if not medicines:
            return "No medicines available"
        
        parts = []
        for med in medicines:
            parts.append(f"- {med.name} {med.dose or ''} ({med.frequency or 'as needed'})")
        return "\n".join(parts)
    
    @staticmethod
    def _format_ocr_data(ocr_data: Optional[OCRData]) -> str:
        """Format OCR data for LLM context."""
        if not ocr_data:
            return "No OCR data available"
        
        # Increase limit to capture more prescription context
        text_limit = 1500
        truncated_text = ocr_data.raw_text[:text_limit]
        if len(ocr_data.raw_text) > text_limit:
            truncated_text += "\n[... additional text truncated ...]"
        
        return f"Prescription/OCR text:\n{truncated_text}"


class OpenRouterLLMProvider(LLMProvider):
    """OpenRouter-based LLM provider using LangChain."""
    llm: Any = None  # Set in __init__; typed Any to accept ChatOpenAI or None
    
    def __init__(self):
        """Initialize OpenRouter provider."""
        try:
            from langchain_openai import ChatOpenAI
            from pydantic import SecretStr
            from app.core.config.config import settings
            
            if not settings.OPENROUTER_API_KEY:
                logger.warning("⚠️ OPENROUTER_API_KEY not set")
                self.llm = None
                return
            
            self.llm = ChatOpenAI(
                api_key=SecretStr(settings.OPENROUTER_API_KEY),
                base_url="https://openrouter.ai/api/v1",
                model="google/gemma-3-27b-it:free",
                temperature=0.3,
                timeout=30,
            ) # type: ignore
            logger.info("✅ OpenRouter LLM provider initialized")
        except Exception as e:
            ChatLogger.log_error("OPENROUTER_INIT", e)
            self.llm = None
    
    def enrich_medicine_info(self, medicine_name: str, ocr_dose: Optional[str] = None,
                           ocr_frequency: Optional[str] = None) -> Dict[str, Any]:
        """Enrich medicine information using OpenRouter."""
        if not self.llm:
            logger.warning(f"OpenRouter LLM not available, returning empty enrichment for {medicine_name}")
            return {}
        
        try:
            prompt = MedicinePrompts.get_enrichment_prompt(medicine_name, ocr_dose, ocr_frequency)
            
            logger.debug(f"Sending enrichment request to OpenRouter for: {medicine_name}")
            response = self.llm.invoke(prompt, config={"callbacks": [langfuse_handler]} if langfuse_handler else None)
            
            # Handle response content safely
            if isinstance(response, str):
                content = response
            elif hasattr(response, 'content'):
                content = response.content if isinstance(response.content, str) else str(response.content)
            else:
                content = str(response)
            
            logger.debug(f"OpenRouter Response: {content[:100]}...")  # type: ignore[index]
            
            # Extract JSON from response
            import re
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                enriched = json.loads(json_match.group())
                ChatLogger.log_llm_enrichment(medicine_name, list(enriched.keys()))
                return enriched
            else:
                logger.warning(f"No JSON found in OpenRouter response for {medicine_name}")
                return {}
        
        except Exception as e:
            ChatLogger.log_error("OPENROUTER_MEDICINE_ENRICHMENT", e)
            return {}
    
    def answer_medicine_query(self, question: str, context: ChatContext) -> str:
        """Answer medicine query using OpenRouter with context."""
        if not self.llm:
            logger.warning("OpenRouter LLM not available, cannot answer query")
            return "Service temporarily unavailable. Please try again later."
        
        try:
            # Prepare context strings
            medicines_data = self._format_medicines(context.ocr_data.medicines if context.ocr_data else [])
            ocr_context = self._format_ocr_data(context.ocr_data)
            current_meds = self._format_medicines(context.current_medicines)
            
            prompt = MedicinePrompts.get_query_response_prompt(
                question, medicines_data, ocr_context, current_meds
            )
            
            logger.debug(f"Sending query to OpenRouter: {question[:50]}...")  # type: ignore[index]
            response = self.llm.invoke(prompt, config={"callbacks": [langfuse_handler]} if langfuse_handler else None)
            
            # Handle response content
            if isinstance(response, str):
                answer = response
            elif hasattr(response, 'content'):
                answer = response.content if isinstance(response.content, str) else str(response.content)
            else:
                answer = str(response)
            
            logger.debug(f"OpenRouter Answer generated: {len(answer)} characters")
            return answer
        
        except Exception as e:
            ChatLogger.log_error("OPENROUTER_QUERY_RESPONSE", e)
            return "Unable to process your query at this moment. Please try again."
    
    @staticmethod
    def _format_medicines(medicines: List[MedicineInfo]) -> str:
        """Format medicines list for LLM context."""
        if not medicines:
            return "No medicines available"
        
        parts = []
        for med in medicines:
            parts.append(f"- {med.name} {med.dose or ''} ({med.frequency or 'as needed'})")
        return "\n".join(parts)
    
    @staticmethod
    def _format_ocr_data(ocr_data: Optional[OCRData]) -> str:
        """Format OCR data for LLM context."""
        if not ocr_data:
            return "No OCR data available"
        
        # Increase limit to capture more prescription context
        text_limit = 1500
        truncated_text = ocr_data.raw_text[:text_limit]
        if len(ocr_data.raw_text) > text_limit:
            truncated_text += "\n[... additional text truncated ...]"
        
        return f"Prescription/OCR text:\n{truncated_text}"


class GroqLLMProvider(LLMProvider):
    """Groq-based LLM provider using LangChain."""
    llm: Any = None  # Set in __init__; typed Any to accept ChatGroq or None
    
    def __init__(self):
        """Initialize Groq provider."""
        try:
            from langchain_groq import ChatGroq
            from pydantic import SecretStr
            from app.core.config.config import settings
            
            if not settings.GROQ_API_KEY:
                logger.warning("⚠️ GROQ_API_KEY not set")
                self.llm = None
                return
            
            self.llm = ChatGroq(
                api_key=SecretStr(settings.GROQ_API_KEY),
                model="llama-3.3-70b-versatile",
                temperature=0.3,
                timeout=30,
            ) # type: ignore
            logger.info("✅ Groq LLM provider initialized")
        except Exception as e:
            ChatLogger.log_error("GROQ_INIT", e)
            self.llm = None
    
    def enrich_medicine_info(self, medicine_name: str, ocr_dose: Optional[str] = None,
                           ocr_frequency: Optional[str] = None) -> Dict[str, Any]:
        """Enrich medicine information using Groq."""
        if not self.llm:
            logger.warning(f"Groq LLM not available, returning empty enrichment for {medicine_name}")
            return {}
        
        try:
            prompt = MedicinePrompts.get_enrichment_prompt(medicine_name, ocr_dose, ocr_frequency)
            
            logger.debug(f"Sending enrichment request to Groq for: {medicine_name}")
            response = self.llm.invoke(prompt, config={"callbacks": [langfuse_handler]} if langfuse_handler else None)
            
            # Handle response content safely
            if isinstance(response, str):
                content = response
            elif hasattr(response, 'content'):
                content = response.content if isinstance(response.content, str) else str(response.content)
            else:
                content = str(response)
            
            logger.debug(f"Groq Response: {content[:100]}...")  # type: ignore[index]
            
            # Extract JSON from response
            import re
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                enriched = json.loads(json_match.group())
                ChatLogger.log_llm_enrichment(medicine_name, list(enriched.keys()))
                return enriched
            else:
                logger.warning(f"No JSON found in Groq response for {medicine_name}")
                return {}
        
        except Exception as e:
            ChatLogger.log_error("GROQ_MEDICINE_ENRICHMENT", e)
            return {}
    
    def answer_medicine_query(self, question: str, context: ChatContext) -> str:
        """Answer medicine query using Groq with context."""
        if not self.llm:
            logger.warning("Groq LLM not available, cannot answer query")
            return "Service temporarily unavailable. Please try again later."
        
        try:
            # Prepare context strings
            medicines_data = self._format_medicines(context.ocr_data.medicines if context.ocr_data else [])
            ocr_context = self._format_ocr_data(context.ocr_data)
            current_meds = self._format_medicines(context.current_medicines)
            
            prompt = MedicinePrompts.get_query_response_prompt(
                question, medicines_data, ocr_context, current_meds
            )
            
            logger.debug(f"Sending query to Groq: {question[:50]}...")  # type: ignore[index]
            response = self.llm.invoke(prompt, config={"callbacks": [langfuse_handler]} if langfuse_handler else None)
            
            # Handle response content
            if isinstance(response, str):
                answer = response
            elif hasattr(response, 'content'):
                answer = response.content if isinstance(response.content, str) else str(response.content)
            else:
                answer = str(response)
            
            logger.debug(f"Groq Answer generated: {len(answer)} characters")
            return answer
        
        except Exception as e:
            ChatLogger.log_error("GROQ_QUERY_RESPONSE", e)
            return "Unable to process your query at this moment. Please try again."
    
    @staticmethod
    def _format_medicines(medicines: List[MedicineInfo]) -> str:
        """Format medicines list for LLM context."""
        if not medicines:
            return "No medicines available"
        
        parts = []
        for med in medicines:
            parts.append(f"- {med.name} {med.dose or ''} ({med.frequency or 'as needed'})")
        return "\n".join(parts)
    
    @staticmethod
    def _format_ocr_data(ocr_data: Optional[OCRData]) -> str:
        """Format OCR data for LLM context."""
        if not ocr_data:
            return "No OCR data available"
        
        # Increase limit to capture more prescription context
        text_limit = 1500
        truncated_text = ocr_data.raw_text[:text_limit]
        if len(ocr_data.raw_text) > text_limit:
            truncated_text += "\n[... additional text truncated ...]"
        
        return f"Prescription/OCR text:\n{truncated_text}"


class EnhancedMedicineChatService:
    """Main enhanced medicine chat service with OCR + LLM integration with fallback."""
    
    def __init__(self):
        """Initialize the enhanced chat service with multiple providers."""
        self.providers = self._initialize_providers()
        self.logger = ChatLogger()
        logger.info(f"🚀 Enhanced Medicine Chat Service initialized with {len(self.providers)} provider(s)")
    
    def _initialize_providers(self) -> List[LLMProvider]:
        """Initialize all available LLM providers in priority order."""
        providers: List[LLMProvider] = []
        
        # 1. Anthropic Claude - Best quality
        anthropic = AnthropicLLMProvider()
        if hasattr(anthropic, 'llm') and anthropic.llm is not None:
            providers.append(anthropic)
            logger.info("✅ Anthropic provider added to fallback chain")
        
        # 2. OpenRouter - Good availability
        openrouter = OpenRouterLLMProvider()
        if hasattr(openrouter, 'llm') and openrouter.llm is not None:
            providers.append(openrouter)
            logger.info("✅ OpenRouter provider added to fallback chain")
        
        # 3. Groq - Fast and free
        groq = GroqLLMProvider()
        if hasattr(groq, 'llm') and groq.llm is not None:
            providers.append(groq)
            logger.info("✅ Groq provider added to fallback chain")
        
        if not providers:
            logger.error("❌ No LLM providers available! Check your API keys.")
        
        return providers
    
    def _get_working_provider(self) -> Optional[LLMProvider]:
        """Get the first available working provider."""
        for provider in self.providers:
            if hasattr(provider, 'llm') and getattr(provider, 'llm', None) is not None:
                return provider
        return None
    
    @log_performance("Service: Chat Process OCR Data")
    def process_ocr_data(self, ocr_text: str) -> OCRData:
        """Process and structure OCR data."""
        try:
            logger.info(f"Processing OCR data: {len(ocr_text)} characters")
            
            # Parse medicines from OCR text using the unified service
            from app.services.ocr.ocr_integration import OCRIntegrationService
            parsed_data = OCRIntegrationService.parse_ocr_for_medicines(ocr_text)
            medicines = parsed_data.get("medicines", [])
            
            ocr_data = OCRData(
                raw_text=ocr_text,
                medicines=medicines,
                extraction_confidence=0.85,  # Default confidence
            )
            
            logger.info(f"OCR processing complete: {len(medicines)} medicines extracted")
            return ocr_data
        
        except Exception as e:
            self.logger.log_error("OCR_PROCESSING", e)
            return OCRData(raw_text=ocr_text, medicines=[])
    
    @log_performance("Service: Chat Enrich with LLM")
    def enrich_with_llm(self, medicine: MedicineInfo, provider_index: int = 0) -> MedicineInfo:
        """Enrich medicine information with LLM knowledge using fallback."""
        # Try each provider in sequence
        for i in range(provider_index, len(self.providers)):
            provider = self.providers[i]
            provider_name = type(provider).__name__.replace('LLMProvider', '')
            
            try:
                logger.debug(f"Enriching medicine '{medicine.name}' with {provider_name}...")
                
                enriched_data = provider.enrich_medicine_info(
                    medicine.name,
                    medicine.dose,
                    medicine.frequency
                )
                
                # If we got data, update and return
                if enriched_data:
                    if "what_it_does" in enriched_data:
                        medicine.what_it_does = enriched_data["what_it_does"]
                    if "side_effects" in enriched_data:
                        medicine.side_effects = enriched_data["side_effects"]
                    if "precautions" in enriched_data:
                        medicine.precautions = enriched_data["precautions"]
                    if "how_to_take" in enriched_data:
                        medicine.how_to_take = enriched_data["how_to_take"]
                    if "interactions" in enriched_data:
                        medicine.interactions = enriched_data["interactions"]
                    
                    medicine.source = "combined"
                    logger.info(f"✅ Enriched '{medicine.name}' using {provider_name}")
                    return medicine
                else:
                    logger.warning(f"⚠️ {provider_name} returned empty enrichment for '{medicine.name}'")
                    
            except Exception as e:
                self.logger.log_error(f"{provider_name.upper()}_ENRICHMENT", e)
                logger.warning(f"⚠️ {provider_name} failed for '{medicine.name}', trying next provider...")
                continue
        
        # All providers failed, return medicine as-is
        logger.warning(f"❌ All providers failed to enrich '{medicine.name}'")
        return medicine
    
    @log_performance("Service: Chat Answer Query")
    def answer_medicine_query(self, context: ChatContext, provider_index: int = 0) -> tuple[str, str]:
        """Answer user's medicine question using full context with fallback."""
        try:
            self.logger.log_chat_request(
                context.question,
                has_image=context.ocr_data is not None,
                ocr_data_available=context.ocr_data is not None
            )
            
            # Log OCR data status for debugging
            if context.ocr_data:
                logger.info(f"📄 OCR data available: {len(context.ocr_data.raw_text)} chars, {len(context.ocr_data.medicines)} medicines")
                ocr_preview = context.ocr_data.raw_text[:300].replace('\n', ' | ')
                logger.info(f"📝 OCR Preview: {ocr_preview}...")
            else:
                logger.warning("⚠️ No OCR data in context")
            
            # Try each provider in sequence
            for i in range(provider_index, len(self.providers)):
                provider = self.providers[i]
                provider_name = type(provider).__name__.replace('LLMProvider', '')
                
                try:
                    logger.info(f"🤖 Attempting query with {provider_name}...")
                    answer = provider.answer_medicine_query(context.question, context)
                    
                    # Check if we got a valid answer (not an error message)
                    if answer and not answer.startswith("Service temporarily unavailable") and not answer.startswith("Unable to process"):
                        logger.info(f"✅ Query answered using {provider_name}: {len(answer)} chars")
                        return answer, provider_name
                    else:
                        logger.warning(f"⚠️ {provider_name} returned error/unavailable message, trying next...")
                        
                except Exception as e:
                    self.logger.log_error(f"{provider_name.upper()}_QUERY", e)
                    logger.warning(f"⚠️ {provider_name} failed, trying next provider...")
                    continue
            
            # All providers failed
            logger.error("❌ All LLM providers failed to answer query")
            return "All AI providers are currently unavailable. Please try again later or check your API key configuration.", "error"
        
        except Exception as e:
            self.logger.log_error("QUERY_ANSWER", e)
            return "Unable to process your request. Please try again.", "error"



# =============================================================================
# Global Service Instance
# =============================================================================

_chat_service: Optional[EnhancedMedicineChatService] = None


def get_chat_service() -> EnhancedMedicineChatService:
    """Get or create the enhanced chat service."""
    global _chat_service
    if _chat_service is None:
        _chat_service = EnhancedMedicineChatService()
    return _chat_service
