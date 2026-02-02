from typing import List, Optional
from datetime import date
from pydantic import BaseModel, HttpUrl, Field

# class ConfidenceField(BaseModel):
#     value: Optional[str] = None
#     confidence: Optional[float] = None  # 0.0 → 1.0
#     raw_text: Optional[str] = None

class OCRRequest(BaseModel):
    prescription_id: str
    image_url: str  # Changed from HttpUrl to str for better compatibility with complex S3 URLs

class Medicine(BaseModel):
    name: Optional[str] = None
    dosage: Optional[str] = None
    frequency: Optional[str] = None
    duration: Optional[str] = None
    instructions: Optional[str] = None

    # confidence: Optional[float] = None
    # raw_text: Optional[str] = None 


class PrescriptionExtracted(BaseModel):
    doctor_name: List[str] = Field(default_factory=list)
    hospital: Optional[str] = None
    date: Optional[str] = None  # Changed from date to str for better AI compatibility
    patient_name: Optional[str] = None
    diagnosis: Optional[str] = None

    medicines: List[Medicine] = Field(default_factory=list)

    tests_advised: List[str] = Field(default_factory=list)
    follow_up: Optional[str] = None

    # overall_confidence: Optional[float] = None

class OCRResponse(BaseModel):
    prescription_id: str
    status: str  # success | needs_review | failed
    extracted_data: Optional[PrescriptionExtracted] = None