#!/usr/bin/env python3
"""
Debug script for Gemini Interactions API testing.
Tests the basic connectivity and request format.
"""

import base64
import os
import sys
from pathlib import Path

# Add the AI_OCR_Service directory to the path
sys.path.insert(0, str(Path(__file__).parent))

from app.core.config import settings

def test_gemini_basic():
    """Test basic Gemini API connectivity"""
    print("=" * 60)
    print("Testing Gemini Interactions API")
    print("=" * 60)
    
    # Check API key
    print(f"\n1. Checking API Key...")
    if not settings.GEMINI_API_KEY:
        print("❌ GEMINI_API_KEY not configured")
        return False
    print(f"✅ GEMINI_API_KEY is set: {settings.get_masked_key('GEMINI_API_KEY')}")
    
    # Check model
    print(f"\n2. Checking Model...")
    print(f"✅ Using model: {settings.GEMINI_MODEL}")
    
    # Test SDK import
    print(f"\n3. Testing google-genai SDK import...")
    try:
        from google import genai
        print(f"✅ google-genai SDK imported successfully")
        print(f"   Version: {genai.__version__ if hasattr(genai, '__version__') else 'unknown'}")
    except ImportError as e:
        print(f"❌ Failed to import google-genai: {e}")
        return False
    
    # Test client initialization
    print(f"\n4. Testing client initialization...")
    try:
        client = genai.Client(api_key=settings.GEMINI_API_KEY)
        print(f"✅ Client initialized successfully")
    except Exception as e:
        print(f"❌ Failed to initialize client: {e}")
        return False
    
    # Test with a simple text prompt (no image)
    print(f"\n5. Testing simple text interaction...")
    try:
        interaction = client.interactions.create(
            model=settings.GEMINI_MODEL,
            input="Say 'test successful' and nothing else."
        )
        print(f"✅ Text interaction successful")
        print(f"   Response: {interaction.outputs[-1].text if interaction.outputs else 'No output'}")
    except Exception as e:
        print(f"❌ Text interaction failed: {e}")
        print(f"   Exception type: {type(e).__name__}")
        import traceback
        traceback.print_exc()
        return False
    
    # Test with image (create a small test image)
    # print(f"\n6. Testing image interaction...")
    # try:
    #     from PIL import Image
    #     import io
        
    #     # Create a simple test image
    #     img = Image.new('RGB', (100, 100), color='blue')
    #     img_bytes = io.BytesIO()
    #     img.save(img_bytes, format='JPEG')
    #     img_bytes = img_bytes.getvalue()
        
    #     image_base64 = base64.b64encode(img_bytes).decode('utf-8')
        
    #     interaction = client.interactions.create(
    #         model=settings.GEMINI_MODEL,
    #         input=[
    #             {"type": "text", "text": "What color is this image?"},
    #             {
    #                 "type": "image",
    #                 "inline_data": {
    #                     "mime_type": "image/jpeg",
    #                     "data": image_base64
    #                 }
    #             }
    #         ]
    #     )
    #     print(f"✅ Image interaction successful")
    #     print(f"   Response: {interaction.outputs[-1].text if interaction.outputs else 'No output'}")
    # except Exception as e:
    #     print(f"❌ Image interaction failed: {e}")
    #     print(f"   Exception type: {type(e).__name__}")
    #     import traceback
    #     traceback.print_exc()
    #     return False
    
    print("\n" + "=" * 60)
    print("✅ All tests passed!")
    print("=" * 60)
    return True

if __name__ == "__main__":
    success = test_gemini_basic()
    sys.exit(0 if success else 1)
