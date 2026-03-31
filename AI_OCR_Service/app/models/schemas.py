from typing import List, Optional
from pydantic import BaseModel, HttpUrl


class OCRRequest(BaseModel):
    prescription_id: str
    image_url: HttpUrl


class Medicine(BaseModel):
    name: Optional[str] = None
    strength: Optional[str] = None
    dosage: Optional[str] = None
    frequency: Optional[str] = None
    duration: Optional[str] = None
    route: Optional[str] = None          # e.g. "oral", "IV", "topical"


class PrescriptionExtracted(BaseModel):
    doctor_name: Optional[str] = None
    hospital: Optional[str] = None
    patient_name: Optional[str] = None   # extracted from prescription if present
    date: Optional[str] = None           # prescription date if present
    medicines: List[Medicine] = []
