"""
Models Package

This package contains Pydantic models and schemas for the application:
- OCRRequest, OCRResponse - OCR API models
- DynamicPrescriptionExtracted - Main prescription data model
- Medicine, PatientInfo, DoctorInfo, etc. - Component models

Example:
    >>> from app.models import OCRRequest, DynamicPrescriptionExtracted
    >>> from app.models.schemas import Medicine, PatientInfo
"""

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.models.schemas import (
        OCRRequest,
        OCRResponse,
        DynamicPrescriptionExtracted,
        Medicine,
        PatientInfo,
        DoctorInfo,
        HospitalInfo,
        VitalSigns,
    )

# Lazy exports for heavy models
__lazy_exports__ = {
    "OCRRequest": "app.models.schemas",
    "OCRResponse": "app.models.schemas",
    "DynamicPrescriptionExtracted": "app.models.schemas",
    "PrescriptionExtracted": "app.models.schemas",  # Alias
    "Medicine": "app.models.schemas",
    "PatientInfo": "app.models.schemas",
    "DoctorInfo": "app.models.schemas",
    "HospitalInfo": "app.models.schemas",
    "VitalSigns": "app.models.schemas",
    "DynamicField": "app.models.schemas",
}


def __getattr__(name: str) -> Any:
    """
    Lazy attribute accessor for models.
    """
    if name in __lazy_exports__:
        module_path = __lazy_exports__[name]
        import importlib
        module = importlib.import_module(module_path)
        return getattr(module, name)
    
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")


__all__ = list(__lazy_exports__.keys())