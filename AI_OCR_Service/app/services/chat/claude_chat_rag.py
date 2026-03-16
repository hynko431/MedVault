"""
Enhanced Medical Chat System with RAG (FAISS Version)
- LangChain for orchestration
- FAISS for vector storage (Windows-compatible, no onnxruntime conflicts)
- Multi-LLM support with automatic fallback
- Multi-modal support (text + images)
- LAZY-LOADED for fast startup
"""

import os
import sys
import logging
from typing import List, Optional, Dict, Any, TYPE_CHECKING
from datetime import datetime, timezone
from io import BytesIO
import pickle
import json
import threading

# Lightweight imports - always fast
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from pydantic import SecretStr

# Lazy imports - heavy modules
_RecursiveCharacterTextSplitter = None

def get_text_splitter():
    """Lazy load RecursiveCharacterTextSplitter"""
    global _RecursiveCharacterTextSplitter
    if _RecursiveCharacterTextSplitter is None:
        from langchain_text_splitters import RecursiveCharacterTextSplitter
        _RecursiveCharacterTextSplitter = RecursiveCharacterTextSplitter
    return _RecursiveCharacterTextSplitter

from app.core.config.config import settings
from app.core.utils.disclaimer import MEDICAL_DISCLAIMER

logger = logging.getLogger(__name__)

# ============================================================================
# LAZY INITIALIZATION HELPERS
# ============================================================================

# Cache for loaded modules/models
_module_cache: Dict[str, Any] = {}
_model_cache: Dict[str, Any] = {}

def _get_cached_module(module_name: str):
    """Get a cached module or import it if not cached"""
    if module_name not in _module_cache:
        logger.debug(f"Lazy importing {module_name}...")
        _module_cache[module_name] = __import__(module_name, fromlist=[''])
    return _module_cache[module_name]

def _get_cached_model(model_type: str, **kwargs):
    """Get a cached model or create it if not cached"""
    cache_key = f"{model_type}:{hash(str(kwargs))}"
    if cache_key not in _model_cache:
        logger.debug(f"Creating {model_type} model...")
        if model_type == "sentence_transformer":
            st = _get_cached_module('sentence_transformers')
            _model_cache[cache_key] = st.SentenceTransformer(kwargs['model_name'])
        elif model_type == "chat_anthropic":
            from langchain_anthropic import ChatAnthropic
            _model_cache[cache_key] = ChatAnthropic(**kwargs)
        elif model_type == "chat_groq":
            from langchain_groq import ChatGroq
            _model_cache[cache_key] = ChatGroq(**kwargs)
        elif model_type == "chat_openai":
            from langchain_openai import ChatOpenAI
            _model_cache[cache_key] = ChatOpenAI(**kwargs)
    return _model_cache[cache_key]


# ============================================================================
# CUSTOM EMBEDDINGS WRAPPER - LAZY LOADING
# ============================================================================

class LocalEmbeddings(Embeddings):
    """Custom embeddings using sentence-transformers - loaded lazily"""
    
    def __init__(self, model_name: str = 'sentence-transformers/all-MiniLM-L6-v2'):
        """Initialize with local sentence transformer model - DEFERRED loading"""
        self.model_name = model_name
        self._model = None  # Lazy loaded
    
    @property
    def model(self):
        """Lazy load the model on first access"""
        if self._model is None:
            logger.info(f"🔄 Loading embeddings model: {self.model_name}")
            try:
                st = _get_cached_module('sentence_transformers')
                self._model = st.SentenceTransformer(self.model_name)
                logger.info(f"✅ Embeddings model ready")
            except Exception as e:
                logger.error(f"❌ Failed to load embeddings: {e}")
                raise
        return self._model
    
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Embed documents"""
        embeddings = self.model.encode(texts, convert_to_tensor=False)
        return [embedding.tolist() for embedding in embeddings]
    
    def embed_query(self, text: str) -> List[float]:
        """Embed a single query"""
        embedding = self.model.encode(text, convert_to_tensor=False)
        return embedding.tolist()


# ============================================================================
# LANGSMITH CONFIGURATION
# ============================================================================

def setup_langsmith():
    """Initialize LangSmith for observability"""
    if os.getenv("LANGSMITH_API_KEY"):
        os.environ["LANGCHAIN_TRACING_V2"] = "true"
        os.environ["LANGCHAIN_PROJECT"] = "medical-chat-rag"
        logger.info("✅ LangSmith tracing enabled")
    else:
        logger.warning("⚠️ LANGSMITH_API_KEY not set. Tracing disabled.")

setup_langsmith()


# ============================================================================
# MEDICAL KNOWLEDGE BASE (FAISS VERSION) - LAZY INITIALIZED
# ============================================================================

class MedicalKnowledgeBase:
    """
    Vector store for medical knowledge retrieval - lazy initialized.
    Uses FAISS for local vector storage - Windows compatible!
    """
    
    def __init__(self, persist_directory: str = "./data/faiss_index"):
        """Initialize knowledge base - DEFERRED loading"""
        self.persist_directory = persist_directory
        self._vector_store: Optional[Any] = None
        self._embeddings: Optional[LocalEmbeddings] = None
        self._initialized = False
    
    def _ensure_initialized(self):
        """Lazy initialization - called on first actual use"""
        if self._initialized:
            return
        
        logger.info("🔄 Initializing MedicalKnowledgeBase (first use)...")
        os.makedirs(self.persist_directory, exist_ok=True)
        
        # Initialize embeddings (loads model)
        self._embeddings = LocalEmbeddings()
        
        # Initialize or load vector store
        try:
            index_file = os.path.join(self.persist_directory, "index.faiss")
            
            if os.path.exists(index_file):
                logger.info("📚 Loading existing FAISS index...")
                from langchain_community.vectorstores import FAISS
                self._vector_store = FAISS.load_local(
                    self.persist_directory,
                    self._embeddings,
                    allow_dangerous_deserialization=True
                )
                logger.info(f"✅ Loaded existing vector store")
            else:
                logger.info("🆕 Creating new medical knowledge base...")
                self._create_initial_knowledge_base()
                logger.info(f"✅ Created new vector store")
            
            self._initialized = True
            logger.info("✅ MedicalKnowledgeBase ready")
            
        except Exception as e:
            logger.error(f"❌ Error initializing vector store: {e}")
            logger.warning("⚠️ Will create new knowledge base on first use")
            raise
    
    def _create_initial_knowledge_base(self):
        """Create initial medical knowledge base with sample data"""
        from langchain_community.vectorstores import FAISS
        TextSplitter = get_text_splitter()
        
        # Sample medical knowledge
        medical_documents = [
            Document(
                page_content="""
                Common prescription abbreviations and their meanings:
                - OD: Once daily - take medication one time per day
                - BD: Twice daily (bis in die) - take medication two times per day, usually 12 hours apart
                - TD/TDS: Three times daily - take medication three times per day
                - QID: Four times daily - take medication four times per day
                - PRN: As needed (pro re nata) - take medication when needed for symptoms
                - AC: Before meals (ante cibum) - take medication before eating
                - PC: After meals (post cibum) - take medication after eating
                - HS: At bedtime (hora somni) - take medication at night before sleep
                - SOS: In case of emergency
                - STAT: Immediately - take medication right away
                """,
                metadata={"source": "medical_abbreviations", "category": "prescriptions", "type": "reference"}
            ),
            Document(
                page_content="""
                Common medication dosage forms and their routes of administration:
                - Tab: Tablet - oral solid form to be swallowed
                - Cap: Capsule - oral solid form containing powder or liquid
                - Syr: Syrup - oral liquid form, usually sweet-tasting
                - Inj: Injection - administered via needle (IM, IV, SC)
                - Susp: Suspension - liquid form with particles, shake before use
                - Oint: Ointment - topical preparation for skin application
                - Drops: Eye or ear drops - topical liquid application
                - Cream: Topical preparation for skin application
                - Powder: Powdered form, may be mixed with liquid
                - Patch: Transdermal patch, applied to skin for absorption
                """,
                metadata={"source": "dosage_forms", "category": "medications", "type": "reference"}
            ),
            Document(
                page_content="""
                Vital signs normal ranges for adults:
                - Blood Pressure: 120/80 mmHg is considered normal
                  - Pre-hypertension: 120-139/80-89 mmHg
                  - Stage 1 Hypertension: 140-159/90-99 mmHg
                  - Stage 2 Hypertension: >160/>100 mmHg
                - Pulse Rate: 60-100 beats per minute is normal for resting heart rate
                  - Bradycardia: <60 bpm (slow heart rate)
                  - Tachycardia: >100 bpm (fast heart rate)
                - Temperature: 98.6°F (37°C) is average normal
                  - Fever: >100.4°F (38°C) suggests infection
                - Respiratory Rate: 12-20 breaths per minute is normal
                - Oxygen Saturation (SpO2): >95% is normal, <90% requires attention
                """,
                metadata={"source": "vital_signs", "category": "clinical", "type": "reference"}
            ),
            Document(
                page_content="""
                Common blood tests and what they measure:
                - CBC: Complete Blood Count
                  - Checks red blood cells (RBC), white blood cells (WBC), and platelets
                  - Used to diagnose anemia, infections, and blood disorders
                - CUE: Complete Urine Examination
                  - Analyzes urine for proteins, glucose, and other abnormalities
                - LFT: Liver Function Test
                  - Measures liver enzymes and bilirubin
                  - Checks liver health and function
                - RFT: Renal Function Test
                  - Measures kidney function through creatinine and urea levels
                - Thyroid Profile: TSH, T3, T4
                  - Checks thyroid hormone levels for hypo/hyperthyroidism
                - Lipid Profile: Total cholesterol, HDL, LDL, triglycerides
                  - Assesses cardiovascular disease risk
                - HbA1c: Hemoglobin A1c
                  - Measures average blood glucose over 3 months
                  - Used for diabetes diagnosis and monitoring
                """,
                metadata={"source": "lab_tests", "category": "diagnostics", "type": "reference"}
            ),
            Document(
                page_content="""
                Common medicine side effects and precautions:
                - Paracetamol (Acetaminophen):
                  - Dose: 500-1000 mg every 4-6 hours
                  - Max daily: 4000 mg
                  - Side effects: Rare, but liver damage with overdose
                  - Precautions: Avoid with liver disease
                
                - Ibuprofen:
                  - Dose: 200-400 mg every 4-6 hours
                  - Side effects: GI upset, heartburn, ulcers with long-term use
                  - Precautions: Avoid with stomach ulcers, kidney disease
                
                - Amoxicillin:
                  - Dose: 250-500 mg three times daily
                  - Side effects: Allergic reactions, diarrhea
                  - Precautions: Avoid if penicillin allergy
                
                - Metformin:
                  - Dose: 500 mg twice daily, up to 2500 mg daily
                  - Side effects: GI upset, metallic taste
                  - Precautions: Monitor kidney function regularly
                """,
                metadata={"source": "common_medicines", "category": "medications", "type": "reference"}
            ),
        ]
        
        # Split documents for better retrieval
        text_splitter = TextSplitter(chunk_size=500, chunk_overlap=50)
        splits = text_splitter.split_documents(medical_documents)
        
        # Create FAISS vector store
        assert self._embeddings is not None, "Embeddings must be initialized"
        self._vector_store = FAISS.from_documents(
            documents=splits,
            embedding=self._embeddings
        )
        self._vector_store.save_local(self.persist_directory)
        logger.info(f"✅ Created vector store with {len(splits)} chunks")
    
    def retrieve(self, query: str, k: int = 3) -> str:
        """Retrieve relevant medical context from vector store"""
        self._ensure_initialized()
        
        if not self._vector_store:
            logger.warning("⚠️ Vector store not initialized")
            return ""
        
        try:
            docs = self._vector_store.similarity_search(query, k=k)
            if not docs:
                logger.info("ℹ️ No relevant documents found")
                return ""
            
            context = "\n\n".join([doc.page_content for doc in docs])
            logger.info(f"✅ Retrieved {len(docs)} relevant documents")
            return context
        
        except Exception as e:
            logger.error(f"❌ Error retrieving context: {e}")
            return ""
    
    def add_documents(self, documents: List[Document]) -> bool:
        """Add new documents to the knowledge base"""
        self._ensure_initialized()
        
        if not self._vector_store:
            logger.warning("⚠️ Vector store not initialized")
            return False
        
        try:
            TextSplitter = get_text_splitter()
            text_splitter = TextSplitter(chunk_size=500, chunk_overlap=50)
            splits = text_splitter.split_documents(documents)
            
            self._vector_store.add_documents(splits)
            self._vector_store.save_local(self.persist_directory)
            
            logger.info(f"✅ Added {len(splits)} new document chunks")
            return True
        
        except Exception as e:
            logger.error(f"❌ Error adding documents: {e}")
            return False


# ============================================================================
# LLM PROVIDERS WITH AUTOMATIC FALLBACK - LAZY VERSION
# ============================================================================

class LLMProvider:
    """Manages LLM providers with automatic fallback - lazy initialization"""
    
    def __init__(self):
        self._providers: Optional[List[Dict[str, Any]]] = None
    
    @property
    def providers(self) -> List[Dict[str, Any]]:
        """Lazy property - initializes providers on first access"""
        if self._providers is None:
            self._providers = self._initialize_providers()
        return self._providers
    
    def _initialize_providers(self) -> List[Dict[str, Any]]:
        """Initialize available LLM providers in priority order"""
        providers = []
        
        # 1. Anthropic Claude - Best for medical tasks
        if settings.ANTHROPIC_API_KEY:
            try:
                from langchain_anthropic import ChatAnthropic
                providers.append({
                    "name": "anthropic",
                    "priority": 1,
                    "llm": ChatAnthropic(
                        api_key=SecretStr(settings.ANTHROPIC_API_KEY),
                        model_name="claude-3-5-sonnet-20241022",
                        temperature=0.7,
                        timeout=30,
                        stop=None
                    )
                })
                logger.info("✅ Anthropic (Claude) provider registered")
            except Exception as e:
                logger.warning(f"⚠️ Failed to initialize Anthropic provider: {e}")
        
        # 2. Groq - Fast and free
        if settings.GROQ_API_KEY:
            try:
                from langchain_groq import ChatGroq
                providers.append({
                    "name": "groq",
                    "priority": 2,
                    "llm": ChatGroq(
                        api_key=SecretStr(settings.GROQ_API_KEY),
                        model="llama-3.3-70b-versatile",
                        temperature=0.7,
                        timeout=30,
                        stop_sequences=None
                    )
                })
                logger.info("✅ Groq provider registered")
            except Exception as e:
                logger.warning(f"⚠️ Failed to initialize Groq provider: {e}")
        
        # 3. OpenRouter - Multiple models available
        if settings.OPENROUTER_API_KEY:
            try:
                from langchain_openai import ChatOpenAI
                providers.append({
                    "name": "openrouter",
                    "priority": 3,
                    "llm": ChatOpenAI(
                        api_key=SecretStr(settings.OPENROUTER_API_KEY),
                        base_url="https://openrouter.ai/api/v1",
                        model="openai/gpt-oss-120b:free",
                        temperature=0.7,
                        timeout=30,
                        stop_sequences=None
                    )
                })
                logger.info("✅ OpenRouter provider registered")
            except Exception as e:
                logger.warning(f"⚠️ Failed to initialize OpenRouter provider: {e}")
        
        if not providers:
            logger.error("❌ No LLM providers configured! Set API keys in .env")
        
        return providers
    
    def get_llm(self) -> tuple[Any, str]:
        """Get the best available LLM"""
        if not self.providers:
            raise RuntimeError(
                "No LLM providers available. Please configure at least one:\n"
                "- ANTHROPIC_API_KEY for Claude\n"
                "- GROQ_API_KEY for Groq (free)\n"
                "- OPENROUTER_API_KEY for OpenRouter"
            )
        
        provider = self.providers[0]
        return provider["llm"], provider["name"]


# ============================================================================
# LAZY INITIALIZATION - Global instances loaded on first use, not import
# ============================================================================

_knowledge_base_instance: Optional[MedicalKnowledgeBase] = None
_llm_provider_instance: Optional["LLMProvider"] = None

def get_knowledge_base() -> MedicalKnowledgeBase:
    """Lazy singleton for knowledge base - loads on first call, not import"""
    global _knowledge_base_instance
    if _knowledge_base_instance is None:
        logger.info("🔄 Creating MedicalKnowledgeBase (lazy)...")
        _knowledge_base_instance = MedicalKnowledgeBase()
        logger.info("✅ MedicalKnowledgeBase created (models not loaded yet)")
    return _knowledge_base_instance

class _LazyKnowledgeBase:
    """Proxy object that lazily loads knowledge_base on first attribute access"""
    _instance: Optional[MedicalKnowledgeBase] = None
    
    def _get_instance(self) -> MedicalKnowledgeBase:
        if self._instance is None:
            _instance = get_knowledge_base()
        return _instance
    
    def __getattr__(self, name: str) -> Any:
        return getattr(self._get_instance(), name)

knowledge_base = _LazyKnowledgeBase()

def get_llm_provider() -> "LLMProvider":
    """Get or create LLM provider singleton"""
    global _llm_provider_instance
    if _llm_provider_instance is None:
        logger.info("🔄 Creating LLMProvider (lazy)...")
        _llm_provider_instance = LLMProvider()
        logger.info("✅ LLMProvider created (providers not loaded yet)")
    return _llm_provider_instance

class _LazyLLMProvider:
    """Proxy object that lazily loads llm_provider on first attribute access"""
    _instance: Optional["LLMProvider"] = None
    
    def _get_instance(self) -> "LLMProvider":
        if self._instance is None:
            _instance = get_llm_provider()
        return _instance
    
    def __getattr__(self, name: str) -> Any:
        return getattr(self._get_instance(), name)

llm_provider = _LazyLLMProvider()


# ============================================================================
# MAIN CHAT FUNCTION
# ============================================================================

def medicine_chat_rag(
    question: str,
    image_data: Optional[str] = None,
    image_format: Optional[str] = "jpeg",
    chat_history: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, Any]:
    """
    Enhanced medical chat with RAG support.
    Heavy models are loaded on first call, not at import.
    """
    logger.info(f"💬 Processing question: {question[:100]}...")
    
    start_time = datetime.now(timezone.utc)
    
    # Step 1: Retrieve relevant medical context (triggers lazy loading)
    logger.info("📚 Retrieving relevant medical knowledge...")
    retrieved_context = knowledge_base.retrieve(question, k=3)
    
    # Step 2: Try each provider in order with fallback
    providers = llm_provider.providers
    
    if not providers:
        logger.error("❌ No LLM providers available")
        raise RuntimeError("No LLM providers configured. Please set ANTHROPIC_API_KEY, GROQ_API_KEY, or OPENROUTER_API_KEY in .env")
    
    last_error = None
    
    for provider_config in providers:
        provider_name = provider_config["name"]
        llm = provider_config["llm"]
        
        try:
            logger.info(f"🤖 Attempting with provider: {provider_name}")
            
            system_prompt = """You are a helpful medical information assistant. Your role is to:
1. Answer questions about medicines, dosages, and medical terms
2. Explain prescription abbreviations and medical concepts
3. Provide general health information

IMPORTANT:
- Always include the medical disclaimer in your response
- Be clear this is for informational purposes only
- Advise users to consult healthcare providers for medical advice
- Use the provided medical knowledge base for accurate information

Medical Knowledge Base:
{context}

Answer the user's question clearly and accurately using the knowledge base when available."""
            
            user_message = f"""Question: {question}

Please provide a clear, helpful answer about this medical topic."""
            
            prompt = ChatPromptTemplate.from_messages([
                ("system", system_prompt),
                ("human", user_message)
            ])
            
            chain = prompt | llm | StrOutputParser()
            
            answer = chain.invoke({
                "context": retrieved_context if retrieved_context else "No specific information found in knowledge base. Providing general information."
            })
            
            if not answer.endswith("\n\n" + MEDICAL_DISCLAIMER):
                answer = answer + "\n\n" + MEDICAL_DISCLAIMER
            
            end_time = datetime.now(timezone.utc)
            processing_time_ms = int((end_time - start_time).total_seconds() * 1000)
            
            response = {
                "answer": answer,
                "provider_used": provider_name,
                "confidence": 0.85,
                "retrieved_context": retrieved_context,
                "metadata": {
                    "started_time": start_time.isoformat(),
                    "completed_time": end_time.isoformat(),
                    "processing_time_ms": processing_time_ms,
                    "has_image": bool(image_data),
                    "question_length": len(question)
                },
                "status": "success"
            }
            
            logger.info(f"✅ Chat completed in {processing_time_ms}ms using {provider_name}")
            return response
            
        except Exception as e:
            last_error = e
            error_msg = str(e)
            
            if "401" in error_msg or "authentication" in error_msg.lower():
                logger.warning(f"⚠️ Authentication failed for {provider_name}: {error_msg}")
            else:
                logger.warning(f"⚠️ Provider {provider_name} failed: {error_msg}")
            
            continue
    
    logger.error(f"❌ All providers failed. Last error: {last_error}")
    raise RuntimeError(f"All AI providers failed. Last error: {str(last_error)}")


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def add_to_knowledge_base(
    content: str,
    metadata: Optional[Dict[str, Any]] = None
) -> bool:
    """Add new content to knowledge base"""
    try:
        doc = Document(
            page_content=content,
            metadata=metadata or {
                "source": "user_uploaded",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        )
        success = knowledge_base.add_documents([doc])
        
        if success:
            logger.info("✅ Added new content to knowledge base")
        else:
            logger.warning("⚠️ Failed to add content to knowledge base")
        
        return success
    
    except Exception as e:
        logger.error(f"❌ Error adding to knowledge base: {e}")
        return False


def process_prescription_for_kb(prescription_data: Dict[str, Any]) -> bool:
    """Process prescription data and add to knowledge base"""
    try:
        content_parts = []
        
        if prescription_data.get("medicines"):
            medicines_text = "Prescribed Medicines:\n"
            for med in prescription_data["medicines"]:
                medicine_name = med.get("name", "Unknown")
                dosage = med.get("dosage", "")
                frequency = med.get("frequency", "")
                medicines_text += f"- {medicine_name} {dosage} {frequency}\n"
            content_parts.append(medicines_text)
        
        if prescription_data.get("diagnosis"):
            content_parts.append(f"Diagnosis: {prescription_data['diagnosis']}\n")
        
        if prescription_data.get("tests_advised"):
            tests_text = "Tests Advised:\n"
            for test in prescription_data["tests_advised"]:
                tests_text += f"- {test}\n"
            content_parts.append(tests_text)
        
        if content_parts:
            content = "\n".join(content_parts)
            metadata = {
                "source": "ocr_prescription",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "type": "prescription"
            }
            return add_to_knowledge_base(content, metadata)
        
        return False
    
    except Exception as e:
        logger.error(f"❌ Error processing prescription: {e}")
        return False


# ============================================================================
# BACKWARDS COMPATIBILITY
# ============================================================================

def medicine_chat(question: str) -> str:
    """Legacy interface - returns just the answer text"""
    try:
        result = medicine_chat_rag(question)
        return result["answer"]
    except Exception as e:
        logger.error(f"Legacy chat failed: {e}")
        raise