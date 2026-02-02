# Quick Reference - 502 Error Fixes

## Problems & Solutions at a Glance

### Problem 1: Google Credentials Invalid JSON
```
❌ Error: JSONDecodeError('Expecting value: line 1 column 1 (char 0)')
```
**Solution:** Fixed `.env` path - removed double quotes
```env
# Before
GOOGLE_APPLICATION_CREDENTIALS=""C:\Users\hulkh\...\credentials.json""

# After
GOOGLE_APPLICATION_CREDENTIALS="C:\Users\hulkh\...\credentials.json"
```

### Problem 2: Wrong Gemini Model Name
```
❌ Error: models/gemini-3-flash is not found for API version v1beta
```
**Solution:** Updated `app/core/config.py`
```python
# Before
GEMINI_MODEL: str = "gemini-3-flash"

# After
GEMINI_MODEL: str = "gemini-1.5-flash"
```

### Problem 3: Pillow Not Installed
```
❌ Error: PIL (Pillow) not installed
```
**Solution:** Install missing dependency
```bash
pip install pillow
```

### Problem 4: Import Error in Search Indexer
```
❌ Error: NameError: name 'ObjectApiResponse' is not defined
```
**Solution:** Removed TYPE_CHECKING imports from function signatures in `app/services/search_indexer.py`
```python
# Changed all return types from
Optional[ObjectApiResponse[Any]]

# To
Optional[Any]
```

---

## Start the Service

```bash
cd C:\Users\hulkh\Downloads\ai_ocr_service\AI_OCR_Service
C:\Users\hulkh\Downloads\ai_ocr_service\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

**Service Ready at:** `http://127.0.0.1:8000`

---

## Call the OCR API (No Credentials Needed!)

```bash
curl -X POST http://127.0.0.1:8000/ocr/extract \
  -H "Content-Type: application/json" \
  -d '{
    "prescription_id": "RX-001",
    "image_url": "https://example.com/prescription.jpg"
  }'
```

---

## API Documentation

- **Swagger UI:** http://127.0.0.1:8000/docs
- **ReDoc:** http://127.0.0.1:8000/redoc

---

## OCR Provider Fallback

```
Google Vision (60s) 
    ↓ fails
Gemini 1.5 Flash (60s)
    ↓ fails
TrOCR Local (120s)
    ↓ fails
502 Error
```

Each provider has automatic retry (3x with exponential backoff)

---

## Files Changed

| File | Change | Impact |
|------|--------|--------|
| `.env` | Fixed path format | ✅ Credentials now readable |
| `app/core/config.py` | Updated Gemini model | ✅ API 404 error fixed |
| `app/services/search_indexer.py` | Removed TYPE_CHECKING imports | ✅ App starts successfully |
| `test_ocr_endpoint.py` | **NEW** | Test the API |
| `API_INTEGRATION_GUIDE.md` | **NEW** | Integration instructions |
| `FIXES_APPLIED.md` | **NEW** | Detailed explanation |

---

## Verification

✅ Service imports successfully
✅ Server running on http://127.0.0.1:8000
✅ Elasticsearch initialized
✅ All OCR providers configured
✅ Multi-provider fallback ready

---

## For Your Backend

Your backend code now:
1. Calls `/ocr/extract` endpoint
2. Doesn't need Google credentials
3. Doesn't need API keys
4. Receives extracted prescription data

```python
import requests

response = requests.post(
    "http://127.0.0.1:8000/ocr/extract",
    json={
        "prescription_id": "RX-12345",
        "image_url": "https://example.com/prescription.jpg"
    }
)

extracted_data = response.json()
```

**That's it!** No credentials, no complexity, just clean API calls.
