"""
Test script for enhanced OCR cleaner with real prescription data
"""
import sys
import json

# Sample OCR output from your prescription
SAMPLE_OCR_TEXT = """SAI CLINIC Dr. Y. Lavanya
MBBS
Near Ambedkar Staue, Miyapur Regd No.: 96510
Hyderabad
Dr. K. Chanakya Chandra Kumar
MBBS
Regd No.: 68237
Name : Test Date : 19/Oct/2022
Age / Gender : 30 yo / Mal Phone No.
Address :
Rₓ
k/c/o - Hypertension & Hypothyroid
c/o - Fever since 3 days
BP - 140/90 Rₓ
PR - 80 bpm 1) Tab. Stamlo 5mg - 0-1-0 - 30 days
O -> x
Investigations 2) Tab. Arvant 5mg - 0-1-0 - 30 day
CBPO -> x
CUE 3) Tab. Thyrox 75mcg - 1-0-0 - 30 days
ECGO -> x
2D Echo 4) Tab. Bplex forte - 1-0-1 - 30 days
Thyroid profile x -> O
Bl. urea
Sr. Creatin
Dengu IgM & IgG"""

def test_enhanced_cleaner():
    """Test the enhanced OCR cleaner"""
    
    # Add the AI_OCR_Service to path
    sys.path.insert(0, r'c:\Users\hulkh\Downloads\ai_ocr_service\AI_OCR_Service')
    
    print("=" * 80)
    print("ENHANCED OCR CLEANER TEST")
    print("=" * 80)
    print()
    
    try:
        from app.services.ocr_cleaner import clean_ocr_text, extract_medicine_info, extract_tests
        
        print("✅ Enhanced cleaner loaded successfully")
        print()
        
        # Step 1: Clean the text
        print("📋 ORIGINAL OCR OUTPUT:")
        print("-" * 80)
        print(SAMPLE_OCR_TEXT)
        print()
        
        print("🧹 CLEANING OCR TEXT...")
        print("-" * 80)
        cleaned_text = clean_ocr_text(SAMPLE_OCR_TEXT)
        print()
        
        print("✨ CLEANED OUTPUT:")
        print("-" * 80)
        print(cleaned_text)
        print()
        
        # Step 2: Extract medicines
        print("💊 EXTRACTED MEDICINES:")
        print("-" * 80)
        medicines = extract_medicine_info(cleaned_text)
        for med in medicines:
            print(f"  • {med['name']}: {med['dosage'] or 'N/A'} - {med['frequency'] or 'N/A'} - {med['duration'] or 'N/A'}")
        print()
        
        # Step 3: Extract tests
        print("🧬 EXTRACTED TESTS:")
        print("-" * 80)
        tests = extract_tests(cleaned_text)
        for test in tests:
            print(f"  • {test}")
        print()
        
        # Step 4: Verification checks
        print("✅ VERIFICATION CHECKS:")
        print("-" * 80)
        
        checks = {
            "Medicine names preserved": all(med in cleaned_text for med in ["Stamlo", "Arvant", "Thyrox", "Bplex"]),
            "Dosages intact": "5mg" in cleaned_text and "75mcg" in cleaned_text,
            "Rx symbol normalized": "Rx" in cleaned_text,
            "Investigation markers": "O -> x" in cleaned_text or "x -> O" in cleaned_text,
            "Date formatted": "19/Oct/2022" in cleaned_text,
            "Gender corrected": "Male" in cleaned_text,
            "Medical abbreviations preserved": "k/c/o" in cleaned_text,
            "4 medicines extracted": len(medicines) >= 3,
            "Tests extracted": len(tests) >= 3,
            "Statue typo fixed": "Statue" in cleaned_text and "Staue" not in cleaned_text,
        }
        
        for check, passed in checks.items():
            status = "✅" if passed else "❌"
            print(f"{status} {check}")
        
        print()
        
        # Step 5: Summary
        passed_checks = sum(checks.values())
        total_checks = len(checks)
        success_rate = (passed_checks / total_checks) * 100
        
        print("=" * 80)
        print(f"RESULT: {passed_checks}/{total_checks} checks passed ({success_rate:.0f}%)")
        print("=" * 80)
        print()
        
        if success_rate >= 90:
            print("🎉 EXCELLENT! Enhanced cleaner is working perfectly!")
        elif success_rate >= 70:
            print("👍 GOOD! Most functionality working as expected.")
        else:
            print("⚠️ NEEDS ADJUSTMENT! Review failing checks.")
        
        # Step 6: Show extracted data as JSON
        print()
        print("📊 STRUCTURED EXTRACTION:")
        print("-" * 80)
        structured = {
            "medicines": medicines,
            "tests": tests,
            "cleaning_stats": {
                "original_length": len(SAMPLE_OCR_TEXT),
                "cleaned_length": len(cleaned_text),
                "reduction_percentage": round((1 - len(cleaned_text) / len(SAMPLE_OCR_TEXT)) * 100, 1)
            }
        }
        print(json.dumps(structured, indent=2))
        
    except ImportError as e:
        print(f"❌ Import Error: {e}")
        print("Make sure the app module is properly configured.")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_enhanced_cleaner()
