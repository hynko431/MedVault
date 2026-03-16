import re
from typing import List, Dict, Any
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
    "k/c/o", "c/o", "h/o", "o/e"
}

# Common medical prefixes that shouldn't be broken
MEDICAL_PREFIXES = ["tab", "cap", "inj", "syr", "dr"]

# Medicine name patterns (common suffixes)
MEDICINE_SUFFIXES = [
    "cillin", "mycin", "azole", "prazole", "dipine", "olol", "sartan",
    "statin", "pril", "lol", "zole", "pine", "tide", "in", "ol"
]


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
    
    # Common prescription terms
    "investigati0ns": "investigations",
    "investigaiions": "investigations",
    "hypertension": "hypertension",  # Common misspelling
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

# OCR character substitution patterns
OCR_CHAR_FIXES = {
    r'\b0(?=[a-z])': 'o',  # 0 -> o at word start (h0spital)
    r'(?<=[a-z])0\b': 'o',  # 0 -> o at word end (investigati0ns)
    r'\b1(?=[a-z])': 'I',  # 1 -> I at word start (1nvestigation)
    r'\b5(?=[a-z])': 'S',  # 5 -> S at word start (5urgery)
    r'(?<=[a-z])5\b': 's',  # 5 -> s at word end (diagnosi5)
}


def fix_common_ocr_errors(text: str) -> str:
    """
    Fix ONLY safe, non-medical OCR errors.
    NEVER touch medicine names or dosages.
    """
    def replace_safe(match):
        word = match.group(0)
        lower = word.lower()
        
        # Check against known safe fixes
        if lower in SAFE_OCR_FIXES:
            corrected = SAFE_OCR_FIXES[lower]
            # Preserve original capitalization pattern
            word_chars = list(str(word))
            if word_chars and word_chars[0].isupper():
                return corrected
        
        return word
    
    # Replace whole words
    text = re.sub(r'\b\w+\b', replace_safe, text)
    
    return text


def fix_character_substitutions(text: str) -> str:
    """
    Fix common OCR character substitutions (0->O, 1->I, 5->S)
    Only in non-medical contexts.
    """
    lines = text.split('\n')
    fixed_lines = []
    
    for line in lines:
        # Skip lines that look like medicine names or dosages
        if re.search(r'\d+\s*(mg|mcg|ml|tab|cap)', line, re.IGNORECASE):
            fixed_lines.append(line)
            continue
        
        # Apply character substitutions
        for pattern, replacement in OCR_CHAR_FIXES.items():
            line = re.sub(pattern, replacement, line)
        
        fixed_lines.append(line)
    
    return '\n'.join(fixed_lines)


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
    """
    # Normalize Rx variations
    text = re.sub(r'\bR[xX]\b', 'Rx', text)
    
    # Preserve numbered lists - ensure space after number
    text = re.sub(r'(\d+)\)', r'\1) ', text)
    
    # Preserve arrows (O -> x, x -> O)
    text = re.sub(r'([Ox0])\s*-+>\s*([Ox0])', r'\1 -> \2', text)
    
    # Fix common date separations (19/Oct/2022, 19-Oct-2022)
    text = re.sub(r'(\d{1,2})\s*/\s*([A-Za-z]{3})\s*/\s*(\d{4})', r'\1/\2/\3', text)
    
    # Preserve dosage patterns (5mg, 75mcg)
    # Ensure no space between number and unit
    text = re.sub(r'(\d+)\s+(mg|mcg|ml|gm|g)', r'\1\2', text, flags=re.IGNORECASE)
    
    return text


def fix_medicine_formatting(text: str) -> str:
    """
    Fix common medicine-related formatting issues:
    - Tab. Stamlo 5mg - 30 days
    - Ensure consistent spacing around medicines
    """
    lines = text.split('\n')
    fixed_lines = []
    
    for line in lines:
        # Fix Tab./Cap./Inj. formatting
        line = re.sub(r'\b(Tab|Cap|Inj|Syr)\.?\s+', r'\1. ', line, flags=re.IGNORECASE)
        
        # Fix spacing around dosage: "5mg" should stay, "5 mg" -> "5mg"
        line = re.sub(r'(\d+)\s+(mg|mcg|ml)\b', r'\1\2', line, flags=re.IGNORECASE)
        
        # Fix frequency notation: "0->x" should be "O -> x" or "o -> x"
        line = re.sub(r'\b0\s*->\s*x\b', 'O -> x', line, flags=re.IGNORECASE)
        line = re.sub(r'\bx\s*->\s*0\b', 'x -> O', line, flags=re.IGNORECASE)
        
        fixed_lines.append(line)
    
    return '\n'.join(fixed_lines)


# ============================================================================
# PHASE 4: JOINING BROKEN WORDS (MEDICAL-AWARE)
# ============================================================================

def is_likely_medicine_name(word: str) -> bool:
    """
    Heuristic to detect if a word is likely a medicine name.
    Medicine names often:
    - End with specific suffixes (-cillin, -mycin, etc.)
    - Are capitalized
    - Have mixed case
    """
    word_lower = word.lower()
    
    # Check for medicine suffixes
    for suffix in MEDICINE_SUFFIXES:
        if word_lower.endswith(suffix):
            return True
    
    # Check for capital letters in middle (CamelCase-like)
    word_str = str(word)
    word_chars = list(word_str)
    first_char = word_chars[0] if word_chars else ""
    word_rest_chars: List[str] = []
    for i in range(1, len(word_chars)):
        word_rest_chars.append(word_chars[i])
    word_rest = "".join(word_rest_chars)
    if len(word) > 3 and first_char.isupper() and any(c.isupper() for c in word_rest):
        return True
    
    return False


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
                
                # Skip if current token is a medical prefix
                if current.lower() in MEDICAL_PREFIXES:
                    new_tokens.append(current)
                    i += 1
                    continue
                
                # Case 1: Both uppercase and short (likely split medicine name)
                if (current.isupper() and next_token.isupper() and 
                    2 <= len(current) <= 5 and 2 <= len(next_token) <= 5):
                    should_join = True
                
                # Case 2: Current ends with consonant, next starts with vowel
                # AND both are short (likely one word split)
                elif (len(current) >= 2 and len(next_token) >= 2 and
                      current[-1].lower() not in 'aeiou' and 
                      next_token[0].lower() in 'aeiou' and
                      3 <= len(current) <= 6 and 2 <= len(next_token) <= 6 and
                      not current[-1].isdigit() and not next_token[0].isdigit()):
                    should_join = True
                
                # Case 3: Both parts together would form a known medicine pattern
                elif is_likely_medicine_name(current + next_token):
                    should_join = True
            
            if should_join:
                joined = tokens[i] + tokens[i + 1]
                new_tokens.append(joined)
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
    
    # Remove noise-only lines
    filtered_lines: List[str] = []
    for line in lines:
        stripped = line.strip()
        # Skip empty or noise-only lines
        if not stripped or re.match(r'^[\s\.\-_=\*]+$', stripped):
            # Keep one blank line for section separation
            if filtered_lines and filtered_lines[-1]:
                filtered_lines.append('')
        else:
            filtered_lines.append(line)
    
    # Remove trailing empty lines
    while filtered_lines and not filtered_lines[-1]:
        filtered_lines.pop()
    
    return "\n".join(filtered_lines)


# ============================================================================
# PHASE 6: SPACING AND PUNCTUATION
# ============================================================================

def fix_spacing(text: str) -> str:
    """
    Fix spacing around punctuation while preserving medical notation:
    - Remove space before punctuation
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
# MAIN CLEANING PIPELINE
# ============================================================================

def clean_ocr_text(raw_text: str) -> str:
    """
    Enhanced OCR cleaning pipeline optimized for medical prescriptions.
    
    Pipeline stages:
    1. Normalize text (whitespace, basic formatting)
    2. Preserve medical structure (Rx, arrows, dates)
    3. Remove OCR artifacts and noise
    4. Fix character substitutions (0->O, 1->I, 5->S)
    5. Fix common OCR errors (safe words only)
    6. Fix medicine formatting
    7. Join broken words (medicine-aware)
    8. Fix spacing and punctuation
    9. Normalize lines
    
    This pipeline is designed to:
    - Preserve all medical information
    - Fix OCR errors without corrupting medicine names
    - Maintain structural integrity of prescriptions
    - Handle Indian medical prescription formats
    """
    logger.info("🧹 Starting enhanced medical OCR cleaning pipeline")
    
    original_length = len(raw_text)
    
    # Stage 1: Basic normalization
    text = normalize_text(raw_text)
    logger.debug("✓ Stage 1: Normalized whitespace and dashes")
    
    # Stage 2: Preserve critical medical structure
    text = preserve_medical_structure(text)
    logger.debug("✓ Stage 2: Preserved Rx symbols, arrows, dates, dosages")
    
    # Stage 3: Remove artifacts
    text = remove_ocr_artifacts(text)
    logger.debug("✓ Stage 3: Removed OCR noise and artifacts")
    
    # Stage 4: Fix character substitutions (context-aware)
    text = fix_character_substitutions(text)
    logger.debug("✓ Stage 4: Fixed character substitutions (0->O, 1->I, 5->S)")
    
    # Stage 5: Fix safe OCR errors
    text = fix_common_ocr_errors(text)
    logger.debug("✓ Stage 5: Fixed common safe OCR errors")
    
    # Stage 6: Fix medicine-specific formatting
    text = fix_medicine_formatting(text)
    logger.debug("✓ Stage 6: Fixed medicine formatting (Tab., dosages, arrows)")
    
    # Stage 7: Join broken words (medicine-aware)
    text = join_broken_words(text)
    logger.debug("✓ Stage 7: Joined broken words (preserved medicine names)")
    
    # Stage 8: Fix spacing and punctuation
    text = fix_spacing(text)
    logger.debug("✓ Stage 8: Fixed spacing around punctuation")
    
    # Stage 9: Normalize lines
    text = normalize_lines(text)
    logger.debug("✓ Stage 9: Normalized line structure")
    
    # Log statistics
    final_length = len(text)
    reduction = ((original_length - final_length) / original_length * 100) if original_length > 0 else 0
    logger.info(f"📊 Cleaning complete: {original_length} → {final_length} chars ({reduction:.1f}% reduction)")
    
    # Log preview with robust extraction
    import itertools
    preview = "".join(itertools.islice(str(text), 500)).replace("\n", "\\n")
    logger.info(f"📄 Clean OCR output (first 500 chars): {preview}")
    
    return text


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def get_cleaning_stats(raw_text: str, cleaned_text: str) -> Dict[str, Any]:
    """
    Get statistics about the cleaning process.
    Useful for monitoring and debugging.
    """
    return {
        "original_length": len(raw_text),
        "cleaned_length": len(cleaned_text),
        "reduction_percentage": ((len(raw_text) - len(cleaned_text)) / len(raw_text) * 100) if len(raw_text) > 0 else 0,
        "original_lines": len(raw_text.split('\n')),
        "cleaned_lines": len(cleaned_text.split('\n')),
        "lines_removed": len(raw_text.split('\n')) - len(cleaned_text.split('\n'))
    }
