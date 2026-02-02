"""
Test script to compare original vs enhanced OCR cleaner
"""

# Sample OCR output from your logs
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
PR - 80 bpm 1) Tab. Stamlo 5mg - 30 days
O -> x
Investigations 2) Tab. Arvant 5mg - 30 day
CBPO -> x
CUE 3) Tab. Thyrox 75mcg - 30 days
ECGO -> x
2D Echo 4) Tab. Bplex forte - 30 days
Thyroid profile x -> O"""


def test_enhanced_cleaner():
    """Test the enhanced OCR cleaner with sample text"""
    
    print("=" * 80)
    print("OCR CLEANER COMPARISON TEST")
    print("=" * 80)
    print()
    
    print("📄 ORIGINAL OCR OUTPUT:")
    print("-" * 80)
    print(SAMPLE_OCR_TEXT)
    print()
    
    # Import the enhanced cleaner
    try:
        from ocr_cleaner_enhanced import clean_ocr_text, get_cleaning_stats
        
        print("✅ Enhanced cleaner loaded successfully")
        print()
        
        # Clean the text
        print("🧹 CLEANING IN PROGRESS...")
        print("-" * 80)
        cleaned_text = clean_ocr_text(SAMPLE_OCR_TEXT)
        print()
        
        # Get statistics
        stats = get_cleaning_stats(SAMPLE_OCR_TEXT, cleaned_text)
        
        print("📊 CLEANING STATISTICS:")
        print("-" * 80)
        print(f"Original length: {stats['original_length']} chars")
        print(f"Cleaned length: {stats['cleaned_length']} chars")
        print(f"Reduction: {stats['reduction_percentage']:.1f}%")
        print(f"Original lines: {stats['original_lines']}")
        print(f"Cleaned lines: {stats['cleaned_lines']}")
        print(f"Lines removed: {stats['lines_removed']}")
        print()
        
        print("✨ ENHANCED CLEANED OUTPUT:")
        print("-" * 80)
        print(cleaned_text)
        print()
        
        # Verification checks
        print("🔍 VERIFICATION CHECKS:")
        print("-" * 80)
        
        checks = {
            "Medicine names preserved": "Stamlo" in cleaned_text and "Thyrox" in cleaned_text,
            "Dosages intact": "5mg" in cleaned_text and "75mcg" in cleaned_text,
            "Rx symbol present": "Rx" in cleaned_text,
            "Investigation markers preserved": "O -> x" in cleaned_text or "x -> O" in cleaned_text,
            "Date formatted": "19/Oct/2022" in cleaned_text,
            "Gender corrected": "Male" in cleaned_text or "male" in cleaned_text,
            "Medical abbreviations preserved": "k/c/o" in cleaned_text and "c/o" in cleaned_text,
        }
        
        for check, passed in checks.items():
            status = "✅" if passed else "❌"
            print(f"{status} {check}")
        
        print()
        
        # Overall assessment
        passed_checks = sum(checks.values())
        total_checks = len(checks)
        success_rate = (passed_checks / total_checks) * 100
        
        print("=" * 80)
        print(f"OVERALL RESULT: {passed_checks}/{total_checks} checks passed ({success_rate:.0f}%)")
        print("=" * 80)
        
        if success_rate >= 90:
            print("🎉 EXCELLENT! The enhanced cleaner works perfectly!")
        elif success_rate >= 70:
            print("👍 GOOD! Minor adjustments may be needed.")
        else:
            print("⚠️ NEEDS WORK! Review the failing checks above.")
        
    except ImportError as e:
        print(f"❌ Error importing enhanced cleaner: {e}")
        print("Make sure ocr_cleaner_enhanced.py is in the same directory.")
    except Exception as e:
        print(f"❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_enhanced_cleaner()
