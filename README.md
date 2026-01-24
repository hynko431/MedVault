# MedVault 🏥
MedVault is a modular AI-powered medical data platform.

## Services

AI_OCR_Service – OCR + document intelligence for medical records

Each service is self-contained and independently deployable.

🔁 End-to-End Flow

Prescription Image
        ↓
OCR Engine (Tesseract / Paddle / Textract / Google Vision OCR API)
        ↓
LLM Structuring + Confidence
        ↓
Confidence Scoring
        ↓
┌─────────────────────────────┐
│ overall_confidence ≥ 0.9     │ → Auto-approved
└─────────────────────────────┘
┌─────────────────────────────┐
│ 0.75 ≤ confidence < 0.9     │ → Pharmacist Review UI
└─────────────────────────────┘
┌─────────────────────────────┐
│ confidence < 0.75           │ → Doctor Verification Required
└─────────────────────────────┘
