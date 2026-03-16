"""
Medicine Response Formatter

Formats medicine information into human-readable responses for chat interactions.
Provides structured formatting for single and multiple medicines.
"""

from typing import List, Optional, Dict, Any
from dataclasses import dataclass

from app.services.chat.models import MedicineInfo
from app.core.utils.disclaimer import MEDICAL_DISCLAIMER, MEDICINE_INFO_DISCLAIMER
from app.core.logging.logger import get_logger

logger = get_logger("medicine_formatter")


class MedicineResponseFormatter:
    """
    Formatter for medicine information responses.
    Creates well-formatted, readable responses about medicines.
    """
    
    @staticmethod
    def format_single_medicine(medicine: MedicineInfo) -> str:
        """
        Format a single medicine into a readable response.
        
        Args:
            medicine: MedicineInfo object
        
        Returns:
            Formatted string with medicine details
        """
        lines = []
        
        # Header with medicine name
        lines.append(f"💊 {medicine.name}")
        lines.append("━" * 40)
        
        # Basic information
        if medicine.dose:
            lines.append(f"📋 **Dosage**: {medicine.dose}")
        
        if medicine.frequency:
            lines.append(f"⏰ **Frequency**: {medicine.frequency}")
        
        if medicine.duration:
            lines.append(f"📅 **Duration**: {medicine.duration}")
        
        if medicine.route:
            lines.append(f"💉 **Route**: {medicine.route.capitalize()}")
        
        lines.append("")  # Empty line
        
        # What it does
        if medicine.what_it_does:
            lines.append("📖 **What it does**:")
            lines.append(f"   {medicine.what_it_does}")
            lines.append("")
        
        # How to take
        if medicine.how_to_take:
            lines.append("📝 **How to take**:")
            lines.append(f"   {medicine.how_to_take}")
            lines.append("")
        
        # Side effects
        if medicine.side_effects:
            lines.append("⚠️ **Common Side Effects**:")
            for effect in medicine.side_effects:
                lines.append(f"   • {effect}")
            lines.append("")
        
        # Precautions
        if medicine.precautions:
            lines.append("🛡️ **Precautions**:")
            for precaution in medicine.precautions:
                lines.append(f"   • {precaution}")
            lines.append("")
        
        # Interactions
        if medicine.interactions:
            lines.append("⚡ **Drug Interactions**:")
            for interaction in medicine.interactions:
                lines.append(f"   • {interaction}")
            lines.append("")
        
        return "\n".join(lines)
    
    @staticmethod
    def format_multiple_medicines(medicines: List[MedicineInfo]) -> str:
        """
        Format multiple medicines into a comprehensive response.
        
        Args:
            medicines: List of MedicineInfo objects
        
        Returns:
            Formatted string with all medicine details
        """
        if not medicines:
            return "No medicines found in the prescription."
        
        lines = []
        lines.append("💊 **Medicine Information**")
        lines.append("=" * 50)
        lines.append("")
        
        # Summary
        lines.append(f"Found {len(medicines)} medicine(s) in your prescription:")
        lines.append("")
        
        # Format each medicine
        for i, medicine in enumerate(medicines, 1):
            lines.append(MedicineResponseFormatter.format_single_medicine(medicine))
            lines.append("")  # Separator between medicines
        
        # Add disclaimer
        lines.append("━" * 50)
        lines.append(MEDICINE_INFO_DISCLAIMER)
        
        return "\n".join(lines)
    
    @staticmethod
    def format_medicine_summary(medicines: List[MedicineInfo]) -> str:
        """
        Create a brief summary of medicines.
        
        Args:
            medicines: List of MedicineInfo objects
        
        Returns:
            Brief summary string
        """
        if not medicines:
            return "No medicines found."
        
        lines = ["**Prescribed Medicines:**"]
        
        for med in medicines:
            details = [med.name]
            if med.dose:
                details.append(med.dose)
            if med.frequency:
                details.append(f"take {med.frequency}")
            
            lines.append(f"• {' - '.join(details)}")
        
        return "\n".join(lines)
    
    @staticmethod
    def format_medicine_comparison(medicines: List[MedicineInfo]) -> str:
        """
        Format medicines in a comparison table style.
        
        Args:
            medicines: List of MedicineInfo objects
        
        Returns:
            Comparison-formatted string
        """
        if not medicines:
            return "No medicines to compare."
        
        lines = []
        lines.append("**Medicine Comparison**")
        lines.append("")
        
        # Create table header
        headers = ["Medicine", "Dose", "Frequency", "Purpose"]
        lines.append(" | ".join(headers))
        lines.append("-" * 60)
        
        # Add each medicine
        for med in medicines:
            row = [
                med.name,
                med.dose or "-",
                med.frequency or "-",
                (med.what_it_does or "-")[:30] + "..." if med.what_it_does and len(med.what_it_does) > 30 else (med.what_it_does or "-")
            ]
            lines.append(" | ".join(row))
        
        return "\n".join(lines)


class ResponseBuilder:
    """
    Builder for constructing complete chat responses.
    Combines medicine information with LLM answers and disclaimers.
    """
    
    @staticmethod
    def build_medicine_query_response(
        llm_answer: str,
        medicines: Optional[List[MedicineInfo]] = None,
        include_disclaimer: bool = True,
        disclaimer_text: Optional[str] = None
    ) -> str:
        """
        Build a complete response for a medicine query.
        
        Args:
            llm_answer: The LLM-generated answer
            medicines: Optional list of medicines to include
            include_disclaimer: Whether to include disclaimer
            disclaimer_text: Custom disclaimer text (uses default if None)
        
        Returns:
            Complete formatted response
        """
        lines = []
        
        # Add LLM answer
        lines.append(llm_answer)
        lines.append("")
        
        # Add medicine details if provided
        if medicines:
            lines.append("━" * 50)
            lines.append("**Your Prescription Medicines:**")
            lines.append("")
            
            for med in medicines:
                lines.append(MedicineResponseFormatter.format_single_medicine(med))
                lines.append("")
        
        # Add disclaimer if requested
        if include_disclaimer:
            lines.append("━" * 50)
            lines.append(disclaimer_text or MEDICINE_INFO_DISCLAIMER)
        
        return "\n".join(lines)
    
    @staticmethod
    def build_prescription_summary_response(
        medicines: List[MedicineInfo],
        doctor_name: Optional[str] = None,
        hospital_name: Optional[str] = None,
        date: Optional[str] = None
    ) -> str:
        """
        Build a summary response for a prescription.
        
        Args:
            medicines: List of medicines in the prescription
            doctor_name: Name of the prescribing doctor
            hospital_name: Name of the hospital/clinic
            date: Prescription date
        
        Returns:
            Formatted prescription summary
        """
        lines = []
        lines.append("📄 **Prescription Summary**")
        lines.append("=" * 50)
        lines.append("")
        
        if doctor_name:
            lines.append(f"👨‍⚕️ **Doctor**: {doctor_name}")
        
        if hospital_name:
            lines.append(f"🏥 **Hospital/Clinic**: {hospital_name}")
        
        if date:
            lines.append(f"📅 **Date**: {date}")
        
        if doctor_name or hospital_name or date:
            lines.append("")
        
        # Add medicines
        lines.append(MedicineResponseFormatter.format_multiple_medicines(medicines))
        
        return "\n".join(lines)
    
    @staticmethod
    def build_error_response(
        error_message: str,
        suggestion: Optional[str] = None
    ) -> str:
        """
        Build an error response with helpful suggestions.
        
        Args:
            error_message: The error message
            suggestion: Optional suggestion for the user
        
        Returns:
            Formatted error response
        """
        lines = []
        lines.append("❌ **Error**")
        lines.append("")
        lines.append(error_message)
        
        if suggestion:
            lines.append("")
            lines.append("💡 **Suggestion**: " + suggestion)
        
        return "\n".join(lines)


class MedicineTableFormatter:
    """
    Format medicines as tables for display.
    Useful for web interfaces or structured output.
    """
    
    @staticmethod
    def to_markdown_table(medicines: List[MedicineInfo]) -> str:
        """
        Convert medicines to a Markdown table.
        
        Args:
            medicines: List of MedicineInfo objects
        
        Returns:
            Markdown table string
        """
        if not medicines:
            return "No medicines to display."
        
        headers = ["Medicine", "Dose", "Frequency", "Duration", "Route"]
        lines = []
        
        # Header row
        lines.append("| " + " | ".join(headers) + " |")
        lines.append("| " + " | ".join(["---"] * len(headers)) + " |")
        
        # Data rows
        for med in medicines:
            row = [
                med.name,
                med.dose or "-",
                med.frequency or "-",
                med.duration or "-",
                med.route or "-"
            ]
            lines.append("| " + " | ".join(row) + " |")
        
        return "\n".join(lines)
    
    @staticmethod
    def to_json(medicines: List[MedicineInfo]) -> List[Dict[str, Any]]:
        """
        Convert medicines to JSON-serializable format.
        
        Args:
            medicines: List of MedicineInfo objects
        
        Returns:
            List of dictionaries
        """
        return [med.to_dict() for med in medicines]


# Convenience functions for direct use
def format_medicine(medicine: MedicineInfo) -> str:
    """Format a single medicine (convenience function)."""
    return MedicineResponseFormatter.format_single_medicine(medicine)


def format_medicines(medicines: List[MedicineInfo]) -> str:
    """Format multiple medicines (convenience function)."""
    return MedicineResponseFormatter.format_multiple_medicines(medicines)