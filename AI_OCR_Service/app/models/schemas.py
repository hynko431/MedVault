from typing import List, Optional, Dict, Any, Union
from datetime import date
from pydantic import BaseModel, HttpUrl, Field, field_validator, model_validator, ConfigDict
import re
import logging

logger = logging.getLogger(__name__)


# ============================================================================
# CORE DYNAMIC MODELS
# ============================================================================

class DynamicField(BaseModel):
    """Represents any field with optional metadata"""
    model_config = ConfigDict(extra='allow')
    
    value: Optional[Any] = None
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
    raw_text: Optional[str] = None


class Medicine(BaseModel):
    """Medicine with flexible fields - any field can be present or absent"""
    model_config = ConfigDict(extra='allow')
    
    name: Optional[str] = None
    dosage: Optional[str] = None
    frequency: Optional[str] = None
    duration: Optional[str] = None
    instructions: Optional[str] = None
    
    # Additional flexible fields
    form: Optional[str] = None  # tablet, capsule, syrup, injection
    route: Optional[str] = None  # oral, topical, IV
    timing: Optional[str] = None  # before food, after food
    quantity: Optional[str] = None  # total tablets/quantity
    refills: Optional[str] = None
    
    # Allow any other fields the AI might extract
    additional_info: Optional[Dict[str, Any]] = Field(default_factory=dict)
    
    @model_validator(mode='before')
    @classmethod
    def capture_additional_fields(cls, values: Any) -> Any:
        """Capture any extra fields into additional_info"""
        if not isinstance(values, dict):
            return values
            
        known_fields = {
            'name', 'dosage', 'frequency', 'duration', 'instructions',
            'form', 'route', 'timing', 'quantity', 'refills', 'additional_info'
        }
        additional = {}
        for key, value in list(values.items()):
            if key not in known_fields and value is not None:
                additional[key] = value
        
        if additional:
            values['additional_info'] = additional
        
        return values


class VitalSigns(BaseModel):
    """Dynamic vital signs - any vital can be present"""
    model_config = ConfigDict(extra='allow')
    
    blood_pressure: Optional[str] = None
    pulse_rate: Optional[str] = None
    temperature: Optional[str] = None
    respiratory_rate: Optional[str] = None
    oxygen_saturation: Optional[str] = None
    weight: Optional[str] = None
    height: Optional[str] = None
    bmi: Optional[str] = None
    
    # Dynamic additional vitals
    additional_vitals: Optional[Dict[str, Any]] = Field(default_factory=dict)
    
    @model_validator(mode='before')
    @classmethod
    def capture_additional_vitals(cls, values: Any) -> Any:
        """Capture any extra vitals"""
        if not isinstance(values, dict):
            return values
            
        known_fields = {
            'blood_pressure', 'pulse_rate', 'temperature', 'respiratory_rate',
            'oxygen_saturation', 'weight', 'height', 'bmi', 'additional_vitals'
        }
        additional = {}
        for key, value in list(values.items()):
            if key not in known_fields and value is not None:
                additional[key] = value
        
        if additional:
            values['additional_vitals'] = additional
        
        return values


class PatientInfo(BaseModel):
    """Dynamic patient information"""
    model_config = ConfigDict(extra='allow')
    
    name: Optional[str] = None
    age: Optional[Union[int, str]] = None
    gender: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    
    # Additional patient fields
    patient_id: Optional[str] = None
    insurance_id: Optional[str] = None
    emergency_contact: Optional[str] = None
    blood_group: Optional[str] = None
    allergies: Optional[List[str]] = Field(default_factory=list)
    
    additional_info: Optional[Dict[str, Any]] = Field(default_factory=dict)
    
    @model_validator(mode='before')
    @classmethod
    def capture_additional_patient_info(cls, values: Any) -> Any:
        """Capture any extra patient information"""
        if not isinstance(values, dict):
            return values
            
        known_fields = {
            'name', 'age', 'gender', 'phone', 'email', 'address',
            'patient_id', 'insurance_id', 'emergency_contact', 
            'blood_group', 'allergies', 'additional_info'
        }
        additional = {}
        for key, value in list(values.items()):
            if key not in known_fields and value is not None:
                additional[key] = value
        
        if additional:
            values['additional_info'] = additional
        
        return values


class DoctorInfo(BaseModel):
    """Dynamic doctor information"""
    model_config = ConfigDict(extra='allow')
    
    name: Optional[str] = None
    names: Optional[List[str]] = Field(default_factory=list)  # Multiple doctors
    qualification: Optional[str] = None
    qualifications: Optional[List[str]] = Field(default_factory=list)
    specialization: Optional[str] = None
    registration_number: Optional[str] = None
    registration_numbers: Optional[List[str]] = Field(default_factory=list)
    
    additional_info: Optional[Dict[str, Any]] = Field(default_factory=dict)
    
    @model_validator(mode='before')
    @classmethod
    def normalize_doctor_data(cls, values: Any) -> Any:
        """Handle both single and multiple doctors"""
        if not isinstance(values, dict):
            return values
            
        # Normalize name/names
        if 'name' in values and values['name'] and 'names' not in values:
            values['names'] = [values['name']]
        elif 'names' in values and values['names'] and not values.get('name'):
            values['name'] = values['names'][0] if values['names'] else None
        
        # Normalize qualifications
        if 'qualification' in values and values['qualification']:
            if 'qualifications' not in values:
                values['qualifications'] = [values['qualification']]
        
        # Normalize registration numbers
        if 'registration_number' in values and values['registration_number']:
            if 'registration_numbers' not in values:
                values['registration_numbers'] = [values['registration_number']]
        
        # Capture additional fields
        known_fields = {
            'name', 'names', 'qualification', 'qualifications', 
            'specialization', 'registration_number', 'registration_numbers',
            'additional_info'
        }
        additional = {}
        for key, value in list(values.items()):
            if key not in known_fields and value is not None:
                additional[key] = value
        
        if additional:
            values['additional_info'] = additional
        
        return values


class HospitalInfo(BaseModel):
    """Dynamic hospital/clinic information"""
    model_config = ConfigDict(extra='allow')
    
    name: Optional[str] = None
    address: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    website: Optional[str] = None
    registration_number: Optional[str] = None
    
    additional_info: Optional[Dict[str, Any]] = Field(default_factory=dict)
    
    @model_validator(mode='before')
    @classmethod
    def capture_additional_hospital_info(cls, values: Any) -> Any:
        """Capture any extra hospital information"""
        if not isinstance(values, dict):
            return values
            
        known_fields = {
            'name', 'address', 'phone', 'email', 'website', 
            'registration_number', 'additional_info'
        }
        additional = {}
        for key, value in list(values.items()):
            if key not in known_fields and value is not None:
                additional[key] = value
        
        if additional:
            values['additional_info'] = additional
        
        return values


# ============================================================================
# MAIN DYNAMIC PRESCRIPTION MODEL
# ============================================================================

class DynamicPrescriptionExtracted(BaseModel):
    """
    Fully dynamic prescription schema that adapts to any prescription format.
    """
    model_config = ConfigDict(extra='allow', validate_assignment=True)
    
    # Core structured sections (optional)
    patient: Optional[PatientInfo] = None
    doctor: Optional[DoctorInfo] = None
    hospital: Optional[HospitalInfo] = None
    vitals: Optional[VitalSigns] = None
    
    # Legacy flat fields (for backward compatibility)
    doctor_name: Optional[List[str]] = Field(default_factory=list)
    hospital_name: Optional[str] = None
    date: Optional[str] = None
    patient_name: Optional[str] = None
    
    # Medical content (always lists, never fail if empty)
    diagnosis: Optional[Union[str, List[str]]] = None
    symptoms: Optional[List[str]] = Field(default_factory=list)
    medical_history: Optional[List[str]] = Field(default_factory=list)
    
    medicines: List[Medicine] = Field(default_factory=list)
    tests_advised: List[str] = Field(default_factory=list)
    
    # Additional structured sections
    follow_up: Optional[str] = None
    advice: Optional[List[str]] = Field(default_factory=list)
    precautions: Optional[List[str]] = Field(default_factory=list)
    dietary_restrictions: Optional[List[str]] = Field(default_factory=list)
    next_visit: Optional[str] = None
    
    # Completely dynamic fields that don't fit anywhere
    additional_fields: Optional[Dict[str, Any]] = Field(default_factory=dict)
    
    # Metadata
    extraction_metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)
    
    @model_validator(mode='before')
    @classmethod
    def handle_dynamic_fields(cls, values: Any) -> Any:
        """
        Intelligently organize dynamic fields into appropriate sections.
        
        SECURITY FIX: Previously this returned non-dict values without validation,
        bypassing all type safety. Now wraps non-dict inputs in a proper structure.
        """
        # SECURITY FIX: Handle non-dict inputs properly
        if not isinstance(values, dict):
            logger.warning(
                f"DynamicPrescriptionExtracted expected dict, got {type(values).__name__}. "
                f"Wrapping in proper structure."
            )
            # Wrap non-dict in a proper structure to maintain validation
            values = {
                "raw_input": str(values),
                "additional_fields": {"original_type": type(values).__name__}
            }
            
        # Known top-level fields
        known_fields = {
            'patient', 'doctor', 'hospital', 'vitals',
            'doctor_name', 'hospital_name', 'date', 'patient_name',
            'diagnosis', 'symptoms', 'medical_history',
            'medicines', 'tests_advised',
            'follow_up', 'advice', 'precautions', 'dietary_restrictions', 'next_visit',
            'additional_fields', 'extraction_metadata'
        }
        
        # Collect unknown fields
        from typing import cast
        unknown_fields: Dict[str, Any] = {}
        values_dict = cast(Dict[str, Any], values)
        for key, value in list(values_dict.items()):
            if key not in known_fields and value is not None:
                unknown_fields[key] = value
        
        # Smart field categorization
        patient_fields = {}
        doctor_fields = {}
        hospital_fields = {}
        vital_fields = {}
        remaining_fields = {}
        
        # Patient-related keywords
        patient_keywords = ['patient', 'age', 'gender', 'phone', 'address', 'email', 'blood_group', 'allergy', 'allergies']
        # Doctor-related keywords
        doctor_keywords = ['doctor', 'physician', 'dr', 'qualification', 'degree', 'specialization', 'registration', 'license']
        # Hospital-related keywords
        hospital_keywords = ['hospital', 'clinic', 'facility', 'center']
        # Vital signs keywords
        vital_keywords = ['bp', 'blood_pressure', 'pulse', 'temperature', 'temp', 'weight', 'height', 'bmi', 'spo2', 'oxygen']
        
        for key, value in unknown_fields.items():
            key_lower = key.lower()
            
            # Categorize based on keywords
            if any(kw in key_lower for kw in patient_keywords):
                patient_fields[key] = value
            elif any(kw in key_lower for kw in doctor_keywords):
                doctor_fields[key] = value
            elif any(kw in key_lower for kw in hospital_keywords):
                hospital_fields[key] = value
            elif any(kw in key_lower for kw in vital_keywords):
                vital_fields[key] = value
            else:
                remaining_fields[key] = value
        
        # Merge categorized fields into structured sections
        if patient_fields:
            if 'patient' not in values_dict or values_dict['patient'] is None:
                values_dict['patient'] = {}
            p_val = values_dict.get('patient')
            if isinstance(p_val, dict):
                p_val.update(patient_fields)
        
        if doctor_fields:
            if 'doctor' not in values_dict or values_dict['doctor'] is None:
                values_dict['doctor'] = {}
            d_val = values_dict.get('doctor')
            if isinstance(d_val, dict):
                d_val.update(doctor_fields)
        
        if hospital_fields:
            if 'hospital' not in values_dict or values_dict['hospital'] is None:
                values_dict['hospital'] = {}
            h_val = values_dict.get('hospital')
            if isinstance(h_val, dict):
                h_val.update(hospital_fields)
        
        if vital_fields:
            if 'vitals' not in values_dict or values_dict['vitals'] is None:
                values_dict['vitals'] = {}
            v_val = values_dict.get('vitals')
            if isinstance(v_val, dict):
                v_val.update(vital_fields)
        
        # Store truly unknown fields
        if remaining_fields:
            if 'additional_fields' not in values_dict:
                values_dict['additional_fields'] = {}
            a_val = values_dict.get('additional_fields')
            if isinstance(a_val, dict):
                a_val.update(remaining_fields)
        
        # Backward compatibility: populate legacy fields from structured data
        if 'doctor' in values_dict and values_dict['doctor']:
            doc_val = values_dict.get('doctor')
            if isinstance(doc_val, dict):
                if 'names' in doc_val and doc_val.get('names'):
                    values_dict['doctor_name'] = doc_val.get('names')
                elif 'name' in doc_val and doc_val.get('name'):
                    name_val = doc_val.get('name')
                    if name_val is not None:
                        values_dict['doctor_name'] = [name_val]
        
        if 'hospital' in values_dict and values_dict['hospital']:
            hosp_val = values_dict.get('hospital')
            if isinstance(hosp_val, dict) and 'name' in hosp_val:
                values_dict['hospital_name'] = hosp_val.get('name')
        
        if 'patient' in values_dict and values_dict['patient']:
            pat_val = values_dict.get('patient')
            if isinstance(pat_val, dict) and 'name' in pat_val:
                values_dict['patient_name'] = pat_val.get('name')
        
        return values_dict
    
    @field_validator('diagnosis', mode='before')
    @classmethod
    def normalize_diagnosis(cls, v: Any) -> Optional[List[str]]:
        """Convert diagnosis to list if it's a string"""
        if isinstance(v, str):
            return [v] if v.strip() else None
        return v
    
    @field_validator('date', mode='before')
    @classmethod
    def clean_date(cls, v: Any) -> Optional[str]:
        """Clean placeholder dates"""
        if isinstance(v, str):
            v_upper = v.strip().upper()
            if v_upper in {"YYYY-MM-DD", "NULL", "NONE", "UNKNOWN", ""}:
                return None
        return v


# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class OCRRequest(BaseModel):
    model_config = ConfigDict(extra='allow')
    
    prescription_id: Optional[str] = "unknown"
    image_url: str = Field(..., min_length=10, description="URL of the prescription image to process")
    
    # Optional: provide schema hints for better extraction
    expected_fields: Optional[List[str]] = None
    extraction_mode: Optional[str] = "dynamic"  # "dynamic" or "strict"


class OCRResponse(BaseModel):
    prescription_id: str
    status: str  # success | needs_review | failed
    extracted_data: Optional[DynamicPrescriptionExtracted] = None
    extraction_mode: Optional[str] = "dynamic"
    fields_extracted: Optional[List[str]] = None  # What fields were actually found


# ============================================================================
# LEGACY SUPPORT (for backward compatibility)
# ============================================================================

# Alias for backward compatibility
PrescriptionExtracted = DynamicPrescriptionExtracted

# ============================================================================
# CHAT API MODELS (Explicitly typed for Pyre2)
# ============================================================================

class ChatRequest(BaseModel):
    question: str
    image_base64: Optional[str] = None
    image_format: str = "jpeg"
    chat_history: Optional[List[Dict[str, str]]] = None
    include_context: Optional[bool] = True

class ImageChatRequest(BaseModel):
    image_base64: str
    image_format: str
    chat_history: Optional[List[Any]] = None
    include_context: Optional[bool] = True

class ChatMetadata(BaseModel):
    provider_used: Optional[str] = None
    confidence: Optional[float] = None
    has_image: Optional[bool] = False
    processing_time_ms: Optional[float] = None

class ChatResponse(BaseModel):
    status: str
    answer: str
    disclaimer: Optional[str] = None
    metadata: Optional[ChatMetadata] = None
    retrieved_context: Optional[str] = None
    suggestions: Optional[List[str]] = None
    error_details: Optional[str] = None

class KnowledgeBaseResponse(BaseModel):
    message: str
    documents_added: int
    status: Optional[str] = "success"