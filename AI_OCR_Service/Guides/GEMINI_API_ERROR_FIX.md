# Gemini API Error Fix - 400 Bad Request

## Issue Reported

```
v1beta/interactions "HTTP/1.1 400 Bad Request"
module 'google.genai' has no attribute 'APIError'
```

## Root Causes

### 1. **Incorrect Exception Handling**
The original code tried to catch exceptions that don't exist in the `google.genai` module:
```python
except genai.APIError as e:  # ❌ APIError doesn't exist
except genai.APIConnectionError as e:  # ❌ APIConnectionError doesn't exist
```

### 2. **Possible Request Format Issue**
The 400 Bad Request error suggests the API request might not be formatted correctly for the current SDK version.

## Solutions Applied

### 1. **Fixed Exception Handling**
```python
# Before (❌ WRONG)
except genai.APIError as e:
    ...
except genai.APIConnectionError as e:
    ...

# After (✅ CORRECT)
except (TimeoutError, TimeoutException) as e:
    ...
except Exception as e:  # Catch any exception from the SDK
    ...
```

### 2. **Improved Request Formatting**
Added better structure for building the interaction input:
```python
# Build the input content list explicitly
content_parts = []
content_parts.append({
    "type": "text",
    "text": extraction_prompt
})
content_parts.append({
    "type": "image",
    "inline_data": {
        "mime_type": "image/jpeg",
        "data": image_base64
    }
})

# Then use it
interaction = client.interactions.create(
    model=model_name,
    input=content_parts
)
```

### 3. **Added Debugging Script**
Created `debug_gemini.py` to test:
- API key configuration
- Client initialization
- Simple text interactions
- Image interactions
- Proper error reporting

## Next Steps

### 1. **Run the Debug Script**
```bash
cd C:\Users\hulkh\Downloads\ai_ocr_service\AI_OCR_Service
python debug_gemini.py
```

This will help identify:
- ✅ If the API key is properly configured
- ✅ If the SDK version supports the Interactions API
- ✅ If the request format is correct
- ❌ Any specific error messages

### 2. **Update google-genai if needed**
```bash
pip install --upgrade google-genai
```

### 3. **Check API Status**
Visit https://console.cloud.google.com to verify:
- API is enabled
- Quota is available
- No service disruptions

## Common Issues & Solutions

| Issue | Solution |
|-------|----------|
| `400 Bad Request` | Run `debug_gemini.py` to see detailed error |
| `module has no attribute 'APIError'` | ✅ Fixed - see exception handling above |
| `GEMINI_API_KEY not set` | Add to `.env`: `GEMINI_API_KEY=sk_live_...` |
| `Model not found` | Ensure using valid model from `get_available_gemini_models()` |

## Testing the Fix

### Option 1: Run Debug Script
```bash
python debug_gemini.py
```

### Option 2: Test OCR Endpoint
```bash
curl -X POST http://localhost:8000/ocr \
  -F "file=@/path/to/prescription.jpg"
```

### Option 3: Python Test
```python
from app.services.gemini_ocr import extract_text_with_gemini

with open("test_image.jpg", "rb") as f:
    text = extract_text_with_gemini(f.read())
    print(text)
```

## Files Modified

1. **`app/services/gemini_ocr.py`**
   - ✅ Fixed exception handling
   - ✅ Improved request formatting
   - ✅ Better error logging

## Technical Details

### Exception Hierarchy in google-genai
The `google.genai` module doesn't expose `APIError` and `APIConnectionError` as top-level attributes. Instead, it raises standard Python exceptions or Google API Core exceptions.

The SDK is designed to:
- Raise standard `Exception` or `ValueError` for most errors
- Include error details in the exception message
- Return structured response objects

### Request Format
The Interactions API expects:
```python
input=[
    {"type": "text", "text": "Your prompt"},
    {"type": "image", "inline_data": {"mime_type": "image/jpeg", "data": "base64_data"}}
]
```

## Rollback Plan (if needed)

If the Interactions API continues to fail, we can fall back to the `generateContent` API:
```python
response = client.models.generate_content(
    model=model_name,
    contents=[...],
    stream=False
)
```

However, this is not recommended as the Interactions API is the newer, recommended approach.

## References

- [Gemini Interactions API Documentation](https://ai.google.dev/gemini-api/docs/interactions)
- [Google GenAI SDK Documentation](https://github.com/googleapis/python-genai)
- [API Status](https://console.cloud.google.com)

## Questions?

1. Run `debug_gemini.py` first to get detailed error information
2. Check the `.env` file has valid `GEMINI_API_KEY`
3. Verify google-genai is installed: `pip show google-genai`
4. Check logs for specific error messages
