import re
import logging
from typing import List, Dict, Tuple, Optional

from app.core.logging.logger import get_logger

logger = get_logger("ocr_cleaner")

# ============================================================================
# MEDICAL CONTEXT AWARENESS
# ============================================================================

# Medical abbreviations that should NOT be "fixed"
MEDICAL_ABBREVIATIONS = {
    "mg", "mcg", "ml", "tab", "cap", "inj", "syr", "dr", "mbbs",
    "bp", "pr", "bpm", "yo", "kg", "cm", "mm", "hrs", "rxn",
    "od", "bd", "td", "qid", "hs", "sos", "stat", "prn",
    "cbp", "cue", "ecg", "echo", "hb", "rbc", "wbc",
    "k/c/o", "c/o", "h/o", "o/e", "bl", "sr", "cr", "igg", "igm"
}

# Common medical prefixes that shouldn't be broken
MEDICAL_PREFIXES = ["tab", "cap", "inj", "syr", "dr"]

# Medicine name patterns (common suffixes)
MEDICINE_SUFFIXES = [
    "cillin", "mycin", "azole", "prazole", "dipine", "olol", "sartan",
    "statin", "pril", "lol", "zole", "pine", "tide", "in", "ol", "fort"
]

# Common medicine names (add more as you encounter them)
COMMON_MEDICINES = {
    "stamlo", "thyrox", "arvant", "bplex", "aspirin", "paracetamol",
    "amoxicillin", "azithromycin", "cefixime", "omeprazole", "atorvastatin",
    "amlodipine", "metoprolol", "losartan", "ramipril", "metformin"
}

# ============================================================================
# PHASE 1: NORMALIZATION
# ============================================================================

def normalize_text(raw_text: str) -> str:
    """
    Safe normalization while preserving medical structure:
    - Normalize whitespace
    - Preserve intentional line breaks
    - Handle dash/hyphen variations
    - Preserve medical symbols (Rx, ->, etc.)
    """
    text = raw_text.strip()
    
    # Normalize multiple spaces to single space (but preserve newlines)
    text = re.sub(r'[ \t]+', ' ', text)
    
    # Normalize multiple blank lines to single blank line
    text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)
    
    # Normalize various dash/hyphen characters to standard hyphen
    # But preserve -> arrows and medical notation
    text = re.sub(r'[\u2010\u2011\u2012\u2013\u2014\u2015](?!>)', '-', text)
    
    # Normalize Rx symbol variations
    text = re.sub(r'[Rr][xX]|Rₓ', 'Rx', text)
    
    return text


# ============================================================================
# PHASE 2: MEDICAL-AWARE OCR ERROR CORRECTION
# ============================================================================

# Safe non-medical OCR fixes
SAFE_OCR_FIXES = {
    "h0spital": "hospital",
    "hospitai": "hospital",
    "clinlc": "clinic",
    "ciinlc": "clinic",
    "medicai": "medical",
    "prescripti0n": "prescription",
    "prescripiion": "prescription",
    "instructi0ns": "instructions",
    "patiient": "patient",
    "pateint": "patient",
    "diagnosi5": "diagnosis",
    "signiture": "signature",
    "datendate": "date",
    "staue": "statue",
    "investigati0ns": "investigations",
    "investigaiions": "investigations",
    "hyperten5ion": "hypertension",
    "hyp0thyroid": "hypothyroid",
    "hypothyr0id": "hypothyroid",
    "diabete5": "diabetes",
    "mal": "male",
    "femaie": "female",
    "yrs": "years",
    "y0": "yo",
}

def is_medical_abbreviation(word: str) -> bool:
    """Check if word is a medical abbreviation that shouldn't be fixed"""
    return word.lower() in MEDICAL_ABBREVIATIONS

def is_likely_medicine_name(word: str) -> bool:
    """Heuristic to detect if a word is likely a medicine name."""
    word_lower = word.lower()
    
    if word_lower in COMMON_MEDICINES:
        return True
    
    for suffix in MEDICINE_SUFFIXES:
        if word_lower.endswith(suffix):
            return True
    
    if len(word) > 3 and word[0].isupper():
        suffix = word[1:]
        if any(c.isupper() for c in suffix):
            return True
    
    return False

def fix_common_ocr_errors(text: str) -> str:
    """Fix ONLY safe, non-medical OCR errors."""
    def replace_safe(match):
        word = match.group(0)
        lower = word.lower()
        if is_medical_abbreviation(word) or is_likely_medicine_name(word):
            return word
        if lower in SAFE_OCR_FIXES:
            corrected = SAFE_OCR_FIXES[lower]
            return corrected.capitalize() if word[0].isupper() else corrected
        return word

    return re.sub(r'\b\w+\b', replace_safe, text)


# ============================================================================
# PHASE 3: STRUCTURE PRESERVATION
# ============================================================================

def preserve_medical_structure(text: str) -> str:
    """Preserve critical medical structure."""
    text = re.sub(r'(\d+)\)', r'\1) ', text)
    text = re.sub(r'([Ox0])\s*-+>\s*([Ox0])', r'\1 -> \2', text)
    text = re.sub(r'(\d{1,2})\s*/\s*([A-Za-z]{3})\s*/\s*(\d{4})', r'\1/\2/\3', text)
    text = re.sub(r'(\d{1,2})\s*-\s*([A-Za-z]{3})\s*-\s*(\d{4})', r'\1-\2-\3', text)
    text = re.sub(r'(\d+)\s+(mg|mcg|ml|gm|g|u|units|iu|cc|l)\b', r'\1\2', text, flags=re.IGNORECASE)
    text = re.sub(r'(?<!\d)-(?=\d)(?![\d\-]*(?:\d{2,}|\d+\s*(?:mg|mcg)))', '-', text)
    return text

def fix_medicine_formatting(text: str) -> str:
    """Fix common medicine-related formatting issues."""
    lines = text.split('\n')
    fixed_lines = []
    for line in lines:
        line = re.sub(r'(Tab\.|Cap\.|Inj\.)\s+([A-Za-z0-9\s]+?)\s+(\d+(?:mg|mcg|ml|gm|g))\b', 
                     r'\1 \2 \3', line, flags=re.IGNORECASE)
        fixed_lines.append(line)
    return '\n'.join(fixed_lines)

# ============================================================================
# PHASE 4: JOINING BROKEN WORDS
# ============================================================================

def join_broken_words(text: str) -> str:
    """Join clearly broken words, but preserve medicine names."""
    lines = text.split('\n')
    cleaned_lines = []
    for line in lines:
        tokens = line.split()
        new_tokens = []
        i = 0
        while i < len(tokens):
            should_join = False
            if i + 1 < len(tokens):
                current = tokens[i]
                next_token = tokens[i + 1]
                combined = current + next_token
                if (current.isupper() and next_token.isupper() and 
                    len(current) <= 4 and len(next_token) <= 4):
                    should_join = True
                elif (len(current) >= 2 and len(next_token) >= 2 and
                      current[-1].lower() not in 'aeiou' and 
                      next_token[0].lower() in 'aeiou' and
                      not is_likely_medicine_name(combined)):
                    should_join = True
            if should_join:
                new_tokens.append(tokens[i] + tokens[i + 1])
                i += 2
            else:
                new_tokens.append(tokens[i])
                i += 1
        cleaned_lines.append(" ".join(new_tokens))
    return "\n".join(cleaned_lines)

# ============================================================================
# PHASE 5: ARTIFACT REMOVAL & LINE NORMALIZATION
# ============================================================================

def remove_ocr_artifacts(text: str) -> str:
    """Remove common OCR artifacts and noise."""
    text = re.sub(r'\.{4,}', '', text)
    text = re.sub(r'(?<![A-Z])\s+\.\s+(?![A-Z])', ' ', text)
    text = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', text)
    text = re.sub(r'([!?]){3,}', r'\1', text)
    lines = text.split('\n')
    cleaned_lines = [line for line in lines if not re.match(r'^[^\w\s]$', line.strip())]
    return '\n'.join(cleaned_lines)

def normalize_lines(text: str) -> str:
    """Clean line structure while preserving medical formatting."""
    lines = [line.rstrip() for line in text.split("\n")]
    filtered_lines = []
    for line in lines:
        stripped = line.strip()
        if stripped and not re.match(r'^[\s\.\-_=\*]+$', stripped):
            filtered_lines.append(line)
        elif not stripped and filtered_lines and filtered_lines[-1]:
            filtered_lines.append(line)
    while filtered_lines and not filtered_lines[-1].strip():
        filtered_lines.pop()
    return "\n".join(filtered_lines)

def fix_spacing(text: str) -> str:
    """Fix spacing around punctuation."""
    text = re.sub(r'\s+([,.:;!?)])(?!>)', r'\1', text)
    text = re.sub(r'([,.:;!?])(?=[A-Za-z])', r'\1 ', text)
    text = re.sub(r'\(\s+', '(', text)
    text = re.sub(r'\s+\)', ')', text)
    text = re.sub(r' {2,}', ' ', text)
    text = re.sub(r'([A-Za-z])\s+:', r'\1:', text)
    text = re.sub(r':\s{2,}', ': ', text)
    return text

# ============================================================================
# PHASE 6: EXTRACTION HELPERS
# ============================================================================

def is_valid_frequency_pattern(text: str) -> bool:
    """Validate if text matches frequency patterns."""
    cleaned = re.sub(r'\s*-\s*', '-', text.strip())
    if re.match(r'^\d+(?:-\d+){2,}$', cleaned):
        return True
    if re.match(r'^[xX](?:-[xXoO0]){2,}$', cleaned):
        return True
    if re.match(r'^[OX](?:-[OX]){2,}$', cleaned, re.IGNORECASE):
        return True
    return False

def extract_frequency_pattern(text: str) -> Optional[str]:
    """Extract and normalize frequency pattern from text."""
    match = re.search(r'((?:\d+|[xXoO0X]|[OX])(?:\s*-+\s*(?:\d+|[xXoO0X]|[OX])){2,})(?:\s*-|\s|$)', text)
    if match:
        freq_text = match.group(1)
        normalized = re.sub(r'\s*-+\s*', '-', freq_text)
        if is_valid_frequency_pattern(normalized):
            return normalized
    return None

def extract_medicine_info(text: str) -> List[Dict[str, str]]:
    """Extract medicine information from prescription text."""
    medicines = []
    seen_names = set()
    pattern = r'(\d+\))\s+(?:Tab\.|Cap\.|Inj\.|T\.)\s*([A-Za-z0-9\-\(\)\s]+?)\s*(?:(\d+(?:mg|mcg|ml|gm|g|u|units|iu))\s*)?(?:(\d+\s*tab)?)?(?=\s*-)'
    matches = re.finditer(pattern, text, re.IGNORECASE)
    
    for match in matches:
        med_name = match.group(2).strip()
        dosage = match.group(3).strip() if match.group(3) else None
        form_info = match.group(4).strip() if match.group(4) else None
        
        if med_name.lower() in seen_names:
            continue
        
        seen_names.add(med_name.lower())
        
        # Extraction logic
        start_pos = int(match.end())
        end_pos = int(start_pos + 200)
        remaining_text = text[start_pos:end_pos]
        
        frequency = extract_frequency_pattern(remaining_text)
        if not frequency:
            freq_match = re.search(r'-+\s*([0-9xXoO\-OX]+?)\s*-+', remaining_text)
            if freq_match:
                candidate = freq_match.group(1).strip()
                if is_valid_frequency_pattern(candidate):
                    frequency = candidate
        
        duration_match = re.search(r'-\s*(\d+\s*(?:days?|weeks?|months?)|Cont\.?|as\s+advised)', remaining_text, re.IGNORECASE)
        duration = duration_match.group(1).strip() if duration_match else None
        
        medicines.append({
            "name": str(med_name),
            "dosage": str(dosage or ""),
            "frequency": str(frequency or ""),
            "duration": str(duration or ""),
            "form": str(form_info or "")
        })
    
    # Strictly cast all values to str to satisfy Pyre2
    results: List[Dict[str, str]] = [{k: str(v or "") for k, v in m.items()} for m in medicines]
    return results

def extract_tests(text: str) -> List[str]:
    """Extract test names from prescription text."""
    tests = []
    test_abbreviations = r'\b(CBP|CBC|CUE|ECG|2D\s*Echo|Thyroid\s*(?:profile)?|Bl\.?\s*urea|Sr\.?\s*Creatinine|Dengue|Dengu|IgM|IgG)\b'
    matches = re.finditer(test_abbreviations, text, re.IGNORECASE)
    for match in matches:
        test_name = match.group(1).strip()
        if test_name and test_name.upper() not in tests:
            tests.append(test_name)
    return tests

# ============================================================================
# MAIN CLEANING PIPELINE
# ============================================================================

def clean_ocr_text(raw_text: str) -> str:
    """Enhanced medical-aware OCR cleaning pipeline."""
    logger.info("Starting enhanced medical-aware OCR cleaning pipeline")
    text = normalize_text(raw_text)
    text = preserve_medical_structure(text)
    text = fix_medicine_formatting(text)
    text = remove_ocr_artifacts(text)
    text = join_broken_words(text)
    text = fix_spacing(text)
    text = fix_common_ocr_errors(text)
    text = normalize_lines(text)
    
    import itertools
    preview = "".join(itertools.islice(text, 500)).replace("\n", "\\n")
    logger.info(f"Clean OCR output (first 500 chars): {preview}")
    return text

def clean_ocr_text_with_extraction(raw_text: str) -> Tuple[str, Dict]:
    """Clean OCR text AND extract structured medical data."""
    cleaned_text = clean_ocr_text(raw_text)
    extraction = {
        "medicines": extract_medicine_info(cleaned_text),
        "tests": extract_tests(cleaned_text),
        "raw_text": cleaned_text
    }
    logger.info(f"Extracted {len(extraction['medicines'])} medicines and {len(extraction['tests'])} tests")
    return cleaned_text, extraction