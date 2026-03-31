import re
from typing import List

def normalize_text(raw_text: str) -> str:
    """
    Safe normalization:
    - Trim whitespace
    - Normalize spaces
    - Normalize blank lines
    """
    text = raw_text.strip()
    text = re.sub(r'[ \t]+', ' ', text)
    text = re.sub(r'\n\s*\n+', '\n', text)
    return text


SAFE_OCR_FIXES = {
    # Organizations / Locations
    "h0spital": "hospital",
    "hospitai": "hospital",
    "clinlc": "clinic",
    "cllnic": "clinic",
    "medicai": "medical",
    "center": "centre",
    "pharmocy": "pharmacy",
    "phormacy": "pharmacy",
    "pormacy": "pharmacy",
    
    # Common labels
    "precription": "prescription",
    "prescriplion": "prescription",
    "address": "address",
    "oddress": "address",
    "phone": "phone",
    "phane": "phone",
    "email": "email",
    "emall": "email",
    
    # Common medical roles
    "dactor": "doctor",
    "doctar": "doctor",
    "physicion": "physician",
    "surgean": "surgeon",
}

def fix_common_ocr_errors(text: str) -> str:
    """
    Fix ONLY safe, non-medical OCR errors.
    Never touch medicine names.
    """
    def replace_safe(match):
        word = match.group(0)
        lower = word.lower()
        if lower in SAFE_OCR_FIXES:
            corrected = SAFE_OCR_FIXES[lower]
            return corrected.capitalize() if word[0].isupper() else corrected
        return word

    return re.sub(r'\b\w+\b', replace_safe, text)


def join_broken_words(text: str) -> str:
    """
    Join clearly broken ALL-CAPS words split by spaces.
    Example: CEFI XIME → CEFIXIME
    """
    lines = text.split('\n')
    cleaned_lines = []

    for line in lines:
        tokens = line.split()
        new_tokens = []
        i = 0

        while i < len(tokens):
            # Check if current and next token are both uppercase and short (likely a split word)
            if (
                i + 1 < len(tokens)
                and tokens[i].isupper()
                and tokens[i + 1].isupper()
                and len(tokens[i]) <= 4
                and len(tokens[i+1]) <= 4
            ):
                new_tokens.append(tokens[i] + tokens[i + 1])
                i += 2
            else:
                new_tokens.append(tokens[i])
                i += 1

        cleaned_lines.append(" ".join(new_tokens))

    return "\n".join(cleaned_lines)

def normalize_lines(text: str) -> str:
    """
    Ensure clean line structure.
    """
    lines = [line.strip() for line in text.split("\n")]
    return "\n".join(lines)

def clean_ocr_text(raw_text: str) -> str:
    """
    Main OCR cleaning pipeline.
    """
    text = normalize_text(raw_text)
    text = fix_common_ocr_errors(text)
    text = join_broken_words(text)
    text = normalize_lines(text)
    return text
