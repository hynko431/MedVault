from typing import List, Optional
from pydantic import BaseModel, HttpUrl

class OCRRequest(BaseModel):
    prescription_id: str
    image_url: HttpUrl
    
class Medicine(BaseModel):
    name: Optional[str]
    strength: Optional[str]
    dosage: Optional[str]
    frequency: Optional[str]
    duration: Optional[str]


class PrescriptionExtracted(BaseModel):
    doctor_name: Optional[str]
    hospital: Optional[str]
    medicines: List[Medicine]
