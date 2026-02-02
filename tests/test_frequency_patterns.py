"""
Test script for enhanced frequency pattern detection
"""
import sys
sys.path.insert(0, r'c:\Users\hulkh\Downloads\ai_ocr_service\AI_OCR_Service')

from app.services.ocr_cleaner import (
    extract_frequency_pattern, 
    is_valid_frequency_pattern,
    extract_medicine_info,
    clean_ocr_text
)

print("=" * 80)
print("FREQUENCY PATTERN DETECTION TEST")
print("=" * 80)
print()

# Test 1: Frequency pattern validation
print("🧪 TEST 1: Pattern Validation")
print("-" * 80)

test_patterns = [
    ("1-0-1", True),        # Valid: morning and evening
    ("0-1-0", True),        # Valid: afternoon only
    ("1-1-1", True),        # Valid: three times a day
    ("0-0-1", True),        # Valid: evening only
    ("1-0-0", True),        # Valid: morning only
    ("2-1-1", True),        # Valid: variable dosage
    ("1-0-1-0", True),      # Valid: four times
    ("0-1-0-1", True),      # Valid: four times (different pattern)
    ("1 - 0 - 1", True),    # Valid with spaces
    ("0 - 0 - 1", True),    # Valid with spaces
    ("invalid", False),     # Invalid
    ("1-2", False),         # Too few parts
    ("a-b-c", False),       # Not digits
]

passed = 0
for pattern, expected in test_patterns:
    result = is_valid_frequency_pattern(pattern)
    status = "✅" if result == expected else "❌"
    print(f"{status} '{pattern}' → {result} (expected {expected})")
    if result == expected:
        passed += 1

print(f"\nValidation Tests: {passed}/{len(test_patterns)} passed")
print()

# Test 2: Frequency pattern extraction
print("🧪 TEST 2: Pattern Extraction")
print("-" * 80)

extraction_tests = [
    ("- 1-0-1 - 30 days", "1-0-1"),
    ("- 0-1-0 - 30 days", "0-1-0"),
    ("- 1 - 0 - 1 - 30 days", "1-0-1"),
    ("- 0 - 0 - 1 - 30 days", "0-0-1"),
    ("- 2-1-1 - 30 days", "2-1-1"),
    ("1-0-1-0", "1-0-1-0"),
    ("no frequency here", None),
    ("- 1 - 30 days", None),  # Not enough parts
]

extracted = 0
for text, expected in extraction_tests:
    result = extract_frequency_pattern(text)
    status = "✅" if result == expected else "❌"
    print(f"{status} '{text}' → {result} (expected {expected})")
    if result == expected:
        extracted += 1

print(f"\nExtraction Tests: {extracted}/{len(extraction_tests)} passed")
print()

# Test 3: Medicine info extraction with frequency
print("🧪 TEST 3: Medicine Extraction with Frequency")
print("-" * 80)

medicine_text = """
1) Tab. Stamlo 5mg - 1-0-1 - 30 days
2) Tab. Arvant 5mg - 0-1-0 - 30 days
3) Tab. Thyrox 75mcg - 1-0-0 - 30 days
4) Tab. Bplex forte - 2-1-1 - 30 days
5) Cap. Amoxicillin 500mg - 1 - 1 - 0 - 10 days
6) Inj. Insulin - 0 - 0 - 1 - Until advised
"""

medicines = extract_medicine_info(medicine_text)

print(f"Found {len(medicines)} medicines:\n")

frequency_checks = [
    ("Stamlo", "1-0-1"),
    ("Arvant", "0-1-0"),
    ("Thyrox", "1-0-0"),
    ("Bplex", "2-1-1"),
]

for med in medicines:
    freq_display = med['frequency'] or "N/A"
    print(f"  💊 {med['name']}")
    print(f"     Dosage: {med['dosage'] or 'N/A'}")
    print(f"     Frequency: {freq_display}")
    print(f"     Duration: {med['duration'] or 'N/A'}")
    print()

# Verify frequency extraction
print("✅ Frequency Pattern Verification:")
for name, expected_freq in frequency_checks:
    found_med = next((m for m in medicines if name in m['name']), None)
    if found_med:
        status = "✅" if found_med['frequency'] == expected_freq else "❌"
        print(f"{status} {name}: {found_med['frequency']} (expected {expected_freq})")
    else:
        print(f"❌ {name}: Not found")

print()

# Test 4: Real prescription scenario
print("🧪 TEST 4: Real Prescription Scenario")
print("-" * 80)

real_ocr = """SAI CLINIC
Name : Test Patient Date : 19/Oct/2022
Age / Gender : 30 yo / Male

Rx

k/c/o - Hypertension, Hypothyroidism
c/o - Fever since 3 days

BP - 140/90
PR - 80 bpm

Rx

1) Tab. Stamlo 5mg - 1 - 0 - 1 - 30 days
2) Tab. Arvant 5mg - 0 - 1 - 0 - 30 days
3) Tab. Thyrox 75mcg - 1 - 0 - 0 - 30 days
4) Tab. Bplex forte - 2 - 1 - 1 - 30 days

Investigations:
- CBP
- ECG
- 2D Echo
"""

from app.services.ocr_cleaner import clean_ocr_text_with_extraction

print("📄 Raw OCR (excerpt):")
print(real_ocr[:200] + "...\n")

cleaned, extraction = clean_ocr_text_with_extraction(real_ocr)

print("📊 Extracted Medicines with Frequencies:")
for med in extraction["medicines"]:
    if med['frequency']:
        print(f"  {med['name']}: {med['frequency']} (Pattern: x-x-x format ✅)")
    else:
        print(f"  {med['name']}: No frequency detected")

print()

# Test 5: Complex frequency patterns
print("🧪 TEST 5: Complex Frequency Patterns")
print("-" * 80)

complex_patterns = {
    "Basic 3-part": "0-1-0",
    "Basic 4-part": "1-0-1-0",
    "With spaces": "1 - 0 - 1",
    "Variable dosage": "2-1-1",
    "Multiple morning": "2-0-1",
    "With extra spaces": "1  -  0  -  1",
}

print("Pattern Detection Results:")
for name, pattern in complex_patterns.items():
    is_valid = is_valid_frequency_pattern(pattern)
    status = "✅" if is_valid else "❌"
    print(f"{status} {name:20} '{pattern}' → Valid: {is_valid}")

print()
print("=" * 80)
print("✨ FREQUENCY PATTERN DETECTION TEST COMPLETE")
print("=" * 80)
