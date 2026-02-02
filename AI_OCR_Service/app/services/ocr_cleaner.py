import re
from typing import List, Dict, Tuple
from app.core.logger import get_logger

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
    # General words
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
    
    # Common prescription terms
    "investigati0ns": "investigations",
    "investigaiions": "investigations",
    "hyperten5ion": "hypertension",
    "hyp0thyroid": "hypothyroid",
    "hypothyr0id": "hypothyroid",
    "diabete5": "diabetes",
    
    # Medical abbreviations OCR errors
    "mal": "male",  # Gender correction
    "femaie": "female",
    "yrs": "years",
    "y0": "yo",  # years old
}

def is_medical_abbreviation(word: str) -> bool:
    """Check if word is a medical abbreviation that shouldn't be fixed"""
    return word.lower() in MEDICAL_ABBREVIATIONS

def is_likely_medicine_name(word: str) -> bool:
    """
    Heuristic to detect if a word is likely a medicine name.
    Medicine names often:
    - End with specific suffixes (-cillin, -mycin, etc.)
    - Are in the known medicines list
    - Have mixed case patterns
    """
    word_lower = word.lower()
    
    # Check if in known medicines
    if word_lower in COMMON_MEDICINES:
        return True
    
    # Check for medicine suffixes
    for suffix in MEDICINE_SUFFIXES:
        if word_lower.endswith(suffix):
            return True
    
    # Check for capital letters in middle (CamelCase-like)
    if len(word) > 3 and word[0].isupper() and any(c.isupper() for c in word[1:]):
        return True
    
    return False

def fix_common_ocr_errors(text: str) -> str:
    """
    Fix ONLY safe, non-medical OCR errors.
    Never touch medicine names or medical abbreviations.
    """
    def replace_safe(match):
        word = match.group(0)
        lower = word.lower()
        
        # Skip medical abbreviations and medicine names
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
    """
    Preserve critical medical structure:
    - Rx symbol and prescription sections
    - Numbered lists (1), 2), 3))
    - Arrows and indicators (O -> x)
    - Date formats
    - Dosage information
    - Frequency patterns (0-1-0, 1-0-1)
    """
    # Preserve numbered lists - ensure space after number
    text = re.sub(r'(\d+)\)', r'\1) ', text)
    
    # Preserve arrows (O -> x, x -> O, 0 -> x, x -> 0)
    text = re.sub(r'([Ox0])\s*-+>\s*([Ox0])', r'\1 -> \2', text)
    
    # Fix common date separations (19/Oct/2022, 19-Oct-2022)
    text = re.sub(r'(\d{1,2})\s*/\s*([A-Za-z]{3})\s*/\s*(\d{4})', r'\1/\2/\3', text)
    text = re.sub(r'(\d{1,2})\s*-\s*([A-Za-z]{3})\s*-\s*(\d{4})', r'\1-\2-\3', text)
    
    # Preserve dosage patterns (5mg, 75mcg) - no space between number and unit
    text = re.sub(r'(\d+)\s+(mg|mcg|ml|gm|g|u|units|iu|cc|l)\b', r'\1\2', text, flags=re.IGNORECASE)
    
    # Preserve frequency patterns (0-1-0, 1-0-1, etc.)
    text = re.sub(r'(?<!\d)-(?=\d)(?![\d\-]*(?:\d{2,}|\d+\s*(?:mg|mcg)))', '-', text)
    
    return text

def fix_medicine_formatting(text: str) -> str:
    """
    Fix common medicine-related formatting issues:
    - Tab. Stamlo 5mg - 30 days
    - Ensure consistent spacing around medicines
    - Preserve dosage information
    """
    lines = text.split('\n')
    fixed_lines = []
    
    for line in lines:
        # Preserve medicine name + dosage patterns
        # Tab. Medicine Name DosageAmount Unit - Duration
        line = re.sub(r'(Tab\.|Cap\.|Inj\.)\s+([A-Za-z0-9\s]+?)\s+(\d+(?:mg|mcg|ml|gm|g))\b', 
                     r'\1 \2 \3', line, flags=re.IGNORECASE)
        fixed_lines.append(line)
    
    return '\n'.join(fixed_lines)

# ============================================================================
# PHASE 4: JOINING BROKEN WORDS (MEDICAL-AWARE)
# ============================================================================

def join_broken_words(text: str) -> str:
    """
    Join clearly broken words, but preserve medicine names.
    Handles:
    - ALL-CAPS words split by spaces (CEFI XIME -> CEFIXIME)
    - Mixed case medical terms
    - Avoids joining actual separate words
    """
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
                
                # Case 1: Both uppercase and short (CEFI XIME -> CEFIXIME)
                if (current.isupper() and next_token.isupper() and 
                    len(current) <= 4 and len(next_token) <= 4):
                    should_join = True
                
                # Case 2: Current ends with consonant, next starts with vowel
                # BUT don't join if it looks like a medicine name
                elif (len(current) >= 2 and len(next_token) >= 2 and
                      current[-1].lower() not in 'aeiou' and 
                      next_token[0].lower() in 'aeiou' and
                      len(current) <= 6 and len(next_token) <= 6 and
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
# PHASE 5: ARTIFACT REMOVAL
# ============================================================================

def remove_ocr_artifacts(text: str) -> str:
    """
    Remove common OCR artifacts and noise:
    - Random dots and excessive punctuation
    - Control characters
    - Preserve medical arrows and indicators
    """
    # Remove repeated dots (but preserve ... if intentional)
    text = re.sub(r'\.{4,}', '', text)  # 4+ dots removed
    
    # Remove isolated dots not part of abbreviations
    text = re.sub(r'(?<![A-Z])\s+\.\s+(?![A-Z])', ' ', text)
    
    # Remove control characters (except newline, tab)
    text = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', text)
    
    # Clean excessive punctuation (but preserve medical notation)
    text = re.sub(r'([!?]){3,}', r'\1', text)
    
    # Remove random single characters on their own line (OCR noise)
    lines = text.split('\n')
    cleaned_lines = [line for line in lines if not re.match(r'^[^\w\s]$', line.strip())]
    text = '\n'.join(cleaned_lines)
    
    return text

def normalize_lines(text: str) -> str:
    """
    Clean line structure while preserving medical formatting:
    - Remove trailing whitespace
    - Remove lines with only noise
    - Preserve intentional blank lines between sections
    """
    lines = [line.rstrip() for line in text.split("\n")]
    
    # Remove noise-only lines but preserve structure
    filtered_lines = []
    for line in lines:
        stripped = line.strip()
        # Keep non-empty lines or intentional blank lines between sections
        if stripped and not re.match(r'^[\s\.\-_=\*]+$', stripped):
            filtered_lines.append(line)
        elif stripped and not filtered_lines:
            # Skip initial noise
            continue
        elif not stripped and filtered_lines and filtered_lines[-1]:
            # Keep one blank line between sections
            filtered_lines.append(line)
    
    # Remove trailing empty lines
    while filtered_lines and not filtered_lines[-1].strip():
        filtered_lines.pop()
    
    return "\n".join(filtered_lines)

def fix_spacing(text: str) -> str:
    """
    Fix spacing around punctuation while preserving medical notation:
    - Remove space before punctuation (except in arrows)
    - Add space after punctuation if missing
    - Preserve medical arrows and symbols
    """
    # Remove space before punctuation (except in arrows)
    text = re.sub(r'\s+([,.:;!?)])(?!>)', r'\1', text)
    
    # Add space after punctuation if missing (except in dosages)
    text = re.sub(r'([,.:;!?])(?=[A-Za-z])', r'\1 ', text)
    
    # Fix parentheses spacing
    text = re.sub(r'\(\s+', '(', text)
    text = re.sub(r'\s+\)', ')', text)
    
    # Multiple spaces to single space
    text = re.sub(r' {2,}', ' ', text)
    
    # Clean spacing around colons in labels (Name : -> Name:)
    text = re.sub(r'([A-Za-z])\s+:', r'\1:', text)
    text = re.sub(r':\s{2,}', ': ', text)
    
    return text

# ============================================================================
# PHASE 6: EXTRACTION HELPERS
# ============================================================================

def is_valid_frequency_pattern(text: str) -> bool:
    """
    Validate if text matches frequency patterns like:
    - Single pattern: "1-0-1", "0-1-0", "2-1-1" (x-x-x where x is digit)
    - Extended: "1-0-1-0", "0-1-0-1-0", etc.
    - With spaces: "1 - 0 - 1", "0 - 1 - 0"
    
    Returns True if it matches the frequency pattern, False otherwise
    """
    # Clean up the text - remove spaces around dashes
    cleaned = re.sub(r'\s*-\s*', '-', text.strip())
    
    # Pattern: one or more digits separated by dashes (minimum 3 parts)
    # Examples: 1-0-1, 0-1-0, 2-1-1, 1-0-1-0, etc.
    if re.match(r'^\d+(?:-\d+){2,}$', cleaned):
        return True
    
    return False

def extract_frequency_pattern(text: str) -> str:
    """
    Extract and normalize frequency pattern from text.
    Converts "1 - 0 - 1" to "1-0-1"
    
    Frequency patterns are x-x-x format (3+ digit groups separated by dashes)
    Examples: 1-0-1, 0-1-0, 2-1-1, 1-0-1-0
    
    Returns normalized frequency string or None if not found
    
    Note: Looks for pattern followed by dash and non-digit (to avoid 
    capturing duration numbers)
    """
    # Look for x-x-x or x-x-x-x patterns followed by dash and space/letter
    # This ensures we don't capture duration numbers
    match = re.search(r'(\d+(?:\s*-\s*\d+){2,})(?:\s*-)', text)
    
    if match:
        freq_text = match.group(1)
        # Normalize: remove spaces around dashes
        normalized = re.sub(r'\s*-\s*', '-', freq_text)
        
        # Validate it's a proper frequency pattern
        if is_valid_frequency_pattern(normalized):
            return normalized
    
    return None # type: ignore

def extract_medicine_info(text: str) -> List[Dict[str, str]]:
    """
    Extract medicine information from prescription text.
    Returns list of dicts with medicine details (without duplicates).
    
    Patterns:
    - "1) Tab. Stamlo 5mg - 0-1-0 - 30 days"
    - "2) Tab. Arvant 5mg - 0-1-0 - 30 day"
    - "3) Tab. Thyrox 75mcg - 1-0-0 - 30 days"
    - "4) Tab. Bplex forte - 1-0-1 - 30 days" (no dosage)
    
    Frequency Patterns (x-x-x format):
    - 0-1-0: Once in afternoon
    - 1-0-0: Once in morning
    - 0-0-1: Once in evening
    - 1-1-1: Three times a day
    - 1-0-1: Morning and evening
    - 2-1-1: Two in morning, once afternoon, once evening
    """
    medicines = []
    seen_names = set()  # Track medicine names to avoid duplicates
    
    # Pattern: Numbered entry + Tab/Cap + medicine name + optional dosage
    # Then look for frequency and duration info
    pattern = r'(\d+\))\s+(?:Tab\.|Cap\.|Inj\.)?\s*([A-Za-z0-9\s]+?)\s*(?:(\d+(?:mg|mcg|ml|gm|g|u|units|iu))\s*)?(?=\s*-)'
    
    matches = re.finditer(pattern, text, re.IGNORECASE)
    
    for match in matches:
        med_name = match.group(2).strip()
        dosage = match.group(3).strip() if match.group(3) else None
        
        # Skip duplicates
        if med_name.lower() in seen_names:
            continue
        
        seen_names.add(med_name.lower())
        
        # Look for frequency and duration in the same/next lines
        end_pos = match.end()
        remaining_text = text[end_pos:end_pos+150]  # Extended search window
        
        # Extract frequency using the new pattern detection
        frequency = extract_frequency_pattern(remaining_text)
        
        # If frequency not found with new method, try alternative patterns
        if not frequency:
            freq_match = re.search(r'-\s*([0-9]{1}[0-9\-]*)\s*-', remaining_text)
            frequency = freq_match.group(1).strip() if freq_match else None
        
        # Extract duration (30 days, etc.)
        duration_match = re.search(r'-\s*(\d+\s*(?:days?|weeks?|months?))\b', remaining_text, re.IGNORECASE)
        duration = duration_match.group(1).strip() if duration_match else None
        
        medicines.append({
            "name": med_name,
            "dosage": dosage,
            "frequency": frequency,
            "duration": duration
        })
    
    return medicines

def extract_tests(text: str) -> List[str]:
    """
    Extract test names from prescription text.
    Looks for common test abbreviations and patterns.
    """
    tests = []
    
    # Common test patterns
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
    """
    Enhanced medical-aware OCR cleaning pipeline with multiple passes:
    1. Normalize text (whitespace, dashes, symbols)
    2. Preserve medical structure (Rx, arrows, lists)
    3. Fix medicine formatting
    4. Remove OCR artifacts
    5. Join broken words (medicine-aware)
    6. Fix spacing around punctuation
    7. Fix safe OCR errors (preserving medicines)
    8. Normalize line structure
    """
    logger.info("Starting enhanced medical-aware OCR cleaning pipeline")

    # Pass 1: Normalize basic formatting
    text = normalize_text(raw_text)
    logger.debug("After normalize_text")
    
    # Pass 2: Preserve medical structure
    text = preserve_medical_structure(text)
    logger.debug("After preserve_medical_structure")
    
    # Pass 3: Fix medicine formatting
    text = fix_medicine_formatting(text)
    logger.debug("After fix_medicine_formatting")
    
    # Pass 4: Remove OCR artifacts
    text = remove_ocr_artifacts(text)
    logger.debug("After remove_ocr_artifacts")
    
    # Pass 5: Join broken words (medicine-aware)
    text = join_broken_words(text)
    logger.debug("After join_broken_words")
    
    # Pass 6: Fix spacing
    text = fix_spacing(text)
    logger.debug("After fix_spacing")
    
    # Pass 7: Fix safe OCR errors
    text = fix_common_ocr_errors(text)
    logger.debug("After fix_common_ocr_errors")
    
    # Pass 8: Normalize lines
    text = normalize_lines(text)
    logger.debug("After normalize_lines")

    preview = text[:500].replace("\n", "\\n")
    logger.info(f"Clean OCR output (first 500 chars): {preview}")
    
    return text

def clean_ocr_text_with_extraction(raw_text: str) -> Tuple[str, Dict]:
    """
    Clean OCR text AND extract structured medical data.
    Returns (cleaned_text, extraction_dict)
    """
    cleaned_text = clean_ocr_text(raw_text)
    
    extraction = {
        "medicines": extract_medicine_info(cleaned_text),
        "tests": extract_tests(cleaned_text),
        "raw_text": cleaned_text
    }
    
    logger.info(f"Extracted {len(extraction['medicines'])} medicines and {len(extraction['tests'])} tests")
    
    return cleaned_text, extraction