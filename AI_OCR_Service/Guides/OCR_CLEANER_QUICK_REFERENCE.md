# OCR Cleaner Quick Reference

## 🚀 Quick Start

### Basic Usage
```python
from app.services.ocr_cleaner import clean_ocr_text

# Clean OCR text
cleaned_text = clean_ocr_text(raw_ocr_output)
```

### With Extraction (including frequencies!)
```python
from app.services.ocr_cleaner import clean_ocr_text_with_extraction

# Clean AND extract structured data with frequencies
cleaned_text, extraction = clean_ocr_text_with_extraction(raw_ocr_output)

medicines = extraction["medicines"]  # List with frequencies included!
tests = extraction["tests"]  # List of test names
```

### Extract Specific Info
```python
from app.services.ocr_cleaner import (
    extract_medicine_info, 
    extract_tests,
    extract_frequency_pattern,
    is_valid_frequency_pattern
)

medicines = extract_medicine_info(cleaned_text)
tests = extract_tests(cleaned_text)
is_valid = is_valid_frequency_pattern("1-0-1")  # True
freq = extract_frequency_pattern("- 1 - 0 - 1 - 30 days")  # "1-0-1"
```

---

## 📊 Output Formats

### Medicine Object (with frequency!)
```json
{
  "name": "Stamlo",
  "dosage": "5mg",
  "frequency": "1-0-1",
  "duration": "30 days"
}
```

### Frequency Patterns (x-x-x format)
```
1-0-1  = Morning + Evening (twice daily)
0-1-0  = Afternoon only (once daily)
1-0-0  = Morning only (once daily)
0-0-1  = Evening only (once daily)
1-1-1  = Three times daily
2-1-1  = Variable dosage (2 morning, 1 afternoon, 1 evening)
1-0-1-0 = Four times
```

### Tests Array
```json
[
  "CBP",
  "ECG",
  "Thyroid profile",
  "2D Echo"
]
```

---

## 🔑 Key Features

| Feature | What It Does |
|---------|------------|
| Medical Abbreviations | Preserves mg, mcg, ml, tab, cap, etc. |
| Medicine Names | Protects from OCR corrections |
| **Frequency Patterns** | Detects 1-0-1, 0-1-0, 2-1-1 formats ✨ |
| Rx Symbol | Normalizes Rx variations (Rₓ → Rx) |
| Investigation Markers | Keeps O → x patterns intact |
| Dosages | Preserves 5mg, 75mcg, etc. |
| Dates | Normalizes 19/Oct/2022 format |
| OCR Errors | Fixes h0spital → hospital safely |
| Artifacts | Removes OCR noise without breaking text |

---

## 🆕 Frequency Pattern Detection

### New: Pattern Validation
```python
from app.services.ocr_cleaner import is_valid_frequency_pattern

is_valid_frequency_pattern("1-0-1")    # → True
is_valid_frequency_pattern("0-1-0")    # → True
is_valid_frequency_pattern("invalid")  # → False
```

### New: Pattern Extraction
```python
from app.services.ocr_cleaner import extract_frequency_pattern

# Automatically normalizes spacing
extract_frequency_pattern("- 1 - 0 - 1 - 30 days")  # → "1-0-1"
extract_frequency_pattern("- 0-1-0 - 30 days")      # → "0-1-0"
extract_frequency_pattern("1  -  0  -  1")          # → "1-0-1"
```

### Automatic in Medicine Extraction
```python
medicines = extract_medicine_info(ocr_text)
# Frequencies automatically detected and included!
for med in medicines:
    print(f"{med['name']}: {med['frequency']}")
    # Stamlo: 1-0-1
    # Thyrox: 1-0-0
```

---

## ⚙️ Configuration

### Add Custom Medicines
Edit `COMMON_MEDICINES` in ocr_cleaner.py:
```python
COMMON_MEDICINES = {
    "stamlo", "thyrox", "arvant", "bplex",
    "your_medicine_here", "another_medicine"
}
```

### Add OCR Error Fixes
Edit `SAFE_OCR_FIXES`:
```python
SAFE_OCR_FIXES = {
    "h0spital": "hospital",
    "your_error": "correction"
}
```

### Extend Medical Abbreviations
Edit `MEDICAL_ABBREVIATIONS`:
```python
MEDICAL_ABBREVIATIONS = {
    "mg", "mcg", "your_abbrev", ...
}
```

---

## 🧪 Testing

Run the test suite:
```bash
# General OCR cleaner test
python test_enhanced_cleaner.py

# Frequency pattern specific test (NEW!)
python test_frequency_patterns.py
```

Expected output:
- 100% checks passed
- All medicines extracted with frequencies
- All tests identified
- Clean normalized text

---

## 🔍 Logging

The cleaner provides debug logging:
```
[INFO] ocr_cleaner - Starting enhanced medical-aware OCR cleaning pipeline
[DEBUG] ocr_cleaner - After normalize_text
[DEBUG] ocr_cleaner - After preserve_medical_structure
...
[INFO] ocr_cleaner - Extracted 4 medicines and 3 tests
[INFO] ocr_cleaner - Clean OCR output (first 500 chars): ...
```

Enable logging:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

---

## 📈 Pipeline Stages

```
Raw OCR Text
    ↓
[1] normalize_text() - Whitespace & symbols
    ↓
[2] preserve_medical_structure() - Rx, arrows, lists
    ↓
[3] fix_medicine_formatting() - Medicine formatting
    ↓
[4] remove_ocr_artifacts() - Remove noise
    ↓
[5] join_broken_words() - Smart word joining
    ↓
[6] fix_spacing() - Punctuation & spaces
    ↓
[7] fix_common_ocr_errors() - Safe corrections
    ↓
[8] normalize_lines() - Final structure
    ↓
Clean Medical Text ✅
    ↓
extract_medicine_info() → Medicines Array (with frequencies!)
extract_tests() → Tests Array
```

---

## 💡 Use Cases

### Case 1: Direct Text Cleaning
```python
from app.services.ocr_cleaner import clean_ocr_text

raw_ocr = "SAI CLINIC Dr. Y. Lavanya..."
clean = clean_ocr_text(raw_ocr)
# Pass to Claude for structured extraction
```

### Case 2: Pre-filter for Claude (with frequencies!)
```python
clean, extraction = clean_ocr_text_with_extraction(raw_ocr)

# Know which medicines and frequencies to expect
known_medicines = [(m["name"], m["frequency"]) for m in extraction["medicines"]]
# [("Stamlo", "1-0-1"), ("Thyrox", "1-0-0")]

# Claude can use this for better extraction
prompt = f"Extract data from: {clean}\nExpected medicines: {known_medicines}"
```

### Case 3: Validation Before Extraction
```python
medicines = extract_medicine_info(clean_text)

if len(medicines) == 0:
    print("Warning: No medicines found")
else:
    print(f"Found {len(medicines)} medicines")
    for med in medicines:
        print(f"  - {med['name']}: {med['dosage']} - {med['frequency']}")
```

---

## 🐛 Troubleshooting

### Problem: Frequencies not extracted
**Solution:** Check if frequency follows pattern "x-x-x" separated by dashes

### Problem: Frequency includes duration numbers (1-0-1-30)
**Solution:** Ensure there's a dash after frequency before duration

### Problem: Invalid frequency pattern detected
**Solution:** Use `is_valid_frequency_pattern()` to validate

### Problem: OCR error not fixed
**Solution:** Add to SAFE_OCR_FIXES dictionary

---

## 📞 API Reference

### clean_ocr_text(raw_text: str) → str
Cleans OCR text and returns normalized string

### clean_ocr_text_with_extraction(raw_text: str) → Tuple[str, Dict]
Cleans text and returns (cleaned_text, extraction_dict)

### extract_medicine_info(text: str) → List[Dict[str, str]]
Extracts medicines with name, dosage, **frequency**, duration

### extract_tests(text: str) → List[str]
Extracts test names from text

### is_valid_frequency_pattern(text: str) → bool
Validates if text is a valid x-x-x frequency pattern

### extract_frequency_pattern(text: str) → str | None
Extracts and normalizes frequency pattern from text

---

## ✅ Validation

Always validate extraction results:
```python
# Check medicine extraction
assert len(medicines) > 0, "No medicines found"
for med in medicines:
    assert "name" in med
    assert "frequency" in med  # New!
    assert med["name"].strip()  # Non-empty name

# Check test extraction
assert len(tests) > 0, "No tests found"
assert all(isinstance(t, str) for t in tests)

# Check frequency validation
for med in medicines:
    if med["frequency"]:
        assert is_valid_frequency_pattern(med["frequency"])
```

---

## 📋 Frequency Reference

**Dosage Timings:**
- **x-0-0:** Once daily (morning)
- **0-x-0:** Once daily (afternoon)
- **0-0-x:** Once daily (evening)
- **x-x-0:** Twice daily (morning + afternoon)
- **x-0-x:** Twice daily (morning + evening)
- **0-x-x:** Twice daily (afternoon + evening)
- **x-x-x:** Three times daily
- **x-x-x-x:** Four times daily

**Common Patterns:**
- `1-0-1` (Stamlo, Arvant) - Hypertension, heart meds
- `1-0-0` (Thyrox) - Thyroid hormone
- `0-1-0` (Pain relievers) - Once daily afternoon
- `1-1-1` (Antibiotics) - Three times daily
- `2-1-1` (Supplements) - Variable dosage

---

**Version:** 2.1 (Enhanced with Frequency Detection)  
**Status:** Production Ready ✅  
**Last Updated:** January 30, 2026

