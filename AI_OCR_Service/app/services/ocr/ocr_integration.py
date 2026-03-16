"""
OCR Integration Service

Provides integration between OCR services and the chat functionality.
Handles OCR extraction, medicine parsing, and data enrichment.
"""

import re
import base64
from typing import Optional, Dict, Any, List

from app.core.logging.logger import get_logger
from app.services.chat.models import MedicineInfo, OCRData

logger = get_logger("ocr_integration")


class OCRIntegrationService:
    """
    Service for integrating OCR functionality with chat and other services.
    Provides methods for extracting and parsing OCR data from images.
    """
    
    # Common medicine name patterns
    MEDICINE_PREFIXES = [
        "T.", "Tab.", "Tablet", "Cap.", "Capsule", "Inj.", "Injection",
        "Syr.", "Syrup", "Susp.", "Suspension", "Drops", "Oint.", "Ointment",
        "Cream", "Gel", "Powder", "Sachet"
    ]
    
    # Common frequency patterns
    FREQUENCY_PATTERNS = [
        r"BD|B\.D\.|bd|b\.d\.",  # Twice daily
        r"TID|T\.I\.D\.|tid|t\.i\.d\.",  # Three times daily
        r"OD|O\.D\.|od|o\.d\.",  # Once daily
        r"QID|Q\.I\.D\.|qid|q\.i\.d\.",  # Four times daily
        r"HS|H\.S\.|hs|h\.s\.",  # At bedtime
        r"AC|A\.C\.|ac|a\.c\.",  # Before meals
        r"PC|P\.C\.|pc|p\.c\.",  # After meals
        r"\d+-\d+-\d+",  # Numeric patterns like 1-0-1
        r"[xXoO]-[xXoO]-[xXoO]",  # Visual patterns like X-O-X
    ]
    
    @staticmethod
    async def extract_ocr_from_image(image_base64: str) -> Optional[str]:
        """
        Extract OCR text from a base64-encoded image.
        
        Args:
            image_base64: Base64-encoded image data
        
        Returns:
            Extracted text or None if extraction failed
            
        Raises:
            ValidationError: If the input is invalid
        """
        try:
            # Validate and decode base64 image
            from app.core.utils.validation import validate_base64_image
            
            image_bytes, image_format = validate_base64_image(image_base64)
            
            # Import vision OCR service
            from app.services.ocr import vision_ocr
            
            # Use the vision OCR service with fallback chain
            text = await vision_ocr.extract_text_with_fallback(image_bytes)
            
            logger.info(f"OCR extraction successful: {len(text) if text else 0} characters")
            return str(text) if text else None
            
        except Exception as e:
            logger.error(f"OCR extraction failed: {str(e)}")
            raise
    
    @staticmethod
    def parse_ocr_for_medicines(ocr_text: str) -> Dict[str, Any]:
        """
        Parse OCR text to extract medicine information.
        
        Args:
            ocr_text: Raw OCR text from prescription
        
        Returns:
            Dictionary with parsed medicines and metadata
        """
        if not ocr_text:
            return {"medicines": [], "raw_text": ""}
        
        medicines = []
        
        # Split text into lines
        lines = ocr_text.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Try to identify medicine lines
            medicine_info = OCRIntegrationService._parse_medicine_line(line)
            
            if medicine_info:
                medicines.append(medicine_info)
                logger.debug(f"Parsed medicine: {medicine_info.name}")
        
        return {
            "medicines": medicines,
            "raw_text": ocr_text,
            "medicine_count": len(medicines)
        }
    
    @staticmethod
    def _parse_medicine_line(line: str) -> Optional[MedicineInfo]:
        """
        Parse a single line to extract medicine information.
        
        Args:
            line: Text line from OCR
        
        Returns:
            MedicineInfo if medicine detected, None otherwise
        """
        # Skip very short lines
        if len(line) < 3:
            return None
        
        # Common patterns for medicine lines
        # Pattern 1: Medicine name with optional prefix
        medicine_patterns = [
            # T. MedicineName (strength)
            r"(?:T\.|Tab\.|Tablet)\s*([A-Za-z][\w\s-]+)\s*(?:\(([\d\s\w]+)\))?",
            # Cap. MedicineName (strength)
            r"(?:Cap\.|Capsule)\s*([A-Za-z][\w\s-]+)\s*(?:\(([\d\s\w]+)\))?",
            # Generic: MedicineName strength
            r"([A-Za-z][\w\s-]+?)\s+(\d+\s*(?:mg|ml|mcg|g|IU|%))",
        ]
        
        for pattern in medicine_patterns:
            match = re.search(pattern, line, re.IGNORECASE)
            if match:
                name = match.group(1).strip()
                strength = match.group(2) if len(match.groups()) > 1 else None
                
                # Extract additional information
                dose = strength
                frequency = OCRIntegrationService._extract_frequency(line)
                duration = OCRIntegrationService._extract_duration(line)
                route = OCRIntegrationService._extract_route(line)
                
                return MedicineInfo(
                    name=name,
                    dose=dose,
                    frequency=frequency,
                    duration=duration,
                    route=route,
                    source="ocr"
                )
        
        # Fallback: Check if line starts with common medicine prefixes
        words = line.split()
        if words:
            first_word = words[0].rstrip('.').lower()
            if first_word in ["t", "tab", "tablet", "cap", "capsule"]:
                # Extract name (rest of first word or next word)
                if len(words) > 1:
                    name = words[1].rstrip('.,;:')
                    # Look for strength in remaining text
                    strength_match = re.search(r'(\d+\s*(?:mg|ml|mcg|g))', line, re.IGNORECASE)
                    dose = strength_match.group(1) if strength_match else None
                    
                    return MedicineInfo(
                        name=name,
                        dose=dose,
                        frequency=OCRIntegrationService._extract_frequency(line),
                        duration=OCRIntegrationService._extract_duration(line),
                        route=OCRIntegrationService._extract_route(line),
                        source="ocr"
                    )
        
        return None
    
    @staticmethod
    def _extract_frequency(line: str) -> Optional[str]:
        """Extract frequency information from a line."""
        # Common frequency patterns
        patterns = [
            r"(BD|B\.D\.|bid)",  # Twice daily
            r"(TID|T\.I\.D\.|tid)",  # Three times daily
            r"(OD|O\.D\.|od)",  # Once daily
            r"(QID|Q\.I\.D\.|qid)",  # Four times daily
            r"(HS|H\.S\.|hs)",  # At bedtime
            r"(\d+-\d+-\d+)",  # Numeric patterns
            r"([xXoO]-[xXoO]-[xXoO])",  # Visual patterns
        ]
        
        for pattern in patterns:
            match = re.search(pattern, line, re.IGNORECASE)
            if match:
                return match.group(1).upper()
        
        return None
    
    @staticmethod
    def _extract_duration(line: str) -> Optional[str]:
        """Extract duration information from a line."""
        # Common duration patterns
        patterns = [
            r"(\d+\s*(?:day|days|week|weeks|month|months))",
            r"(cont\.?|continue|ongoing)",
            r"(\d+\s*D/W)",  # Days per week
        ]
        
        for pattern in patterns:
            match = re.search(pattern, line, re.IGNORECASE)
            if match:
                return match.group(1)
        
        return None
    
    @staticmethod
    def _extract_route(line: str) -> Optional[str]:
        """Extract route of administration from a line."""
        routes = {
            "oral": ["oral", "po", "per os", "by mouth"],
            "iv": ["iv", "intravenous", "i.v."],
            "im": ["im", "intramuscular", "i.m."],
            "sc": ["sc", "subcutaneous", "subcut", "s.c."],
            "topical": ["topical", "top", "apply"],
            "inhalation": ["inh", "inhalation", "inhaler"],
            "sublingual": ["sublingual", "sl", "sub lingual"],
        }
        
        line_lower = line.lower()
        for route, keywords in routes.items():
            if any(kw in line_lower for kw in keywords):
                return route
        
        # Default to oral if it's a tablet/capsule
        if any(kw in line_lower for kw in ["tablet", "capsule", "tab", "cap", "t.", "cap."]):
            return "oral"
        
        return None
    
    @staticmethod
    def clean_ocr_text(text: str) -> str:
        """
        Clean OCR text by removing artifacts and normalizing.
        
        Args:
            text: Raw OCR text
        
        Returns:
            Cleaned text
        """
        if not text:
            return ""
        
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Fix common OCR errors
        replacements = {
            '0': 'O',  # Zero to Oh in some contexts
            '1': 'l',  # One to ell (context dependent)
            '|': 'I',  # Pipe to capital I
        }
        
        # Don't apply globally - only in specific contexts
        # For now, just strip and normalize
        
        # Remove non-printable characters
        text = ''.join(char for char in text if char.isprintable() or char in '\n\r\t')
        
        return text.strip()
    
    @staticmethod
    def format_for_chat(ocr_data: OCRData) -> str:
        """
        Format OCR data for chat context.
        
        Args:
            ocr_data: OCR data object
        
        Returns:
            Formatted string for LLM context
        """
        if not ocr_data or not ocr_data.raw_text:
            return "No prescription data available."
        
        lines = ["Prescription Information:"]
        lines.append("=" * 40)
        
        # Add medicines section
        if ocr_data.medicines:
            lines.append("\nMedicines:")
            for i, med in enumerate(ocr_data.medicines, 1):
                lines.append(f"{i}. {med.name}")
                if med.dose:
                    lines.append(f"   Dose: {med.dose}")
                if med.frequency:
                    lines.append(f"   Frequency: {med.frequency}")
                if med.duration:
                    lines.append(f"   Duration: {med.duration}")
                if med.route:
                    lines.append(f"   Route: {med.route}")
        
        # Add raw text summary
        lines.append(f"\nFull Prescription Text:")
        lines.append(ocr_data.raw_text[:500])  # Limit to 500 chars
        if len(ocr_data.raw_text) > 500:
            lines.append("... [truncated]")
        
        return "\n".join(lines)


# Global service instance
_ocr_integration_service: Optional[OCRIntegrationService] = None


def get_ocr_service() -> OCRIntegrationService:
    """Get or create the OCR integration service."""
    global _ocr_integration_service
    if _ocr_integration_service is None:
        _ocr_integration_service = OCRIntegrationService()
    return _ocr_integration_service


# Alias for compatibility with chat.py imports
OCRIntegration = OCRIntegrationService