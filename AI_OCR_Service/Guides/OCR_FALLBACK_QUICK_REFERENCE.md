# 🚀 OCR Fallback Quick Reference

## At a Glance

**OCR Priority Chain (NEW):**
```
1️⃣ Gemini (GEMINI_API_KEY) → Fast, API-based
2️⃣ Google Vision (GOOGLE_APPLICATION_CREDENTIALS) → Accurate, credentials needed
3️⃣ TrOCR (No credentials) → Local fallback
```

**LLM Priority Chain (UNCHANGED):**
```
Anthropic → OpenRouter → Groq
(No changes made - as requested)
```

---

## Setup (5 minutes)

### Step 1: Set Environment Variables

**`.env` file:**
```env
GEMINI_API_KEY=your_gemini_key
GOOGLE_APPLICATION_CREDENTIALS=path/to/credentials.json
```

### Step 2: Verify Installation

```bash
# All packages already in requirements.txt
pip install -r requirements.txt
```

### Step 3: Test

```bash
# Start the server
uvicorn app.main:app --reload

# Test OCR endpoint
curl -X POST "http://localhost:8000/api/ocr/extract" \
  -H "Content-Type: application/json" \
  -d '{"image_url": "s3://bucket/image.jpg", "prescription_id": "RX-001"}'
```

---

## How It Works

### **When Request Comes In:**

1. ✅ **Try Gemini First** (fastest)
   - If succeeds → Return result
   - If fails → Log and continue to step 2

2. ✅ **Try Google Vision** (most accurate)
   - If succeeds → Return result
   - If fails → Log and continue to step 3

3. ✅ **Try TrOCR** (local fallback)
   - If succeeds → Return result
   - If fails → Return HTTP 502 with error details

### **Automatic Retries**

Each provider gets **2 retries** with exponential backoff:
- 1st retry: Wait 1 second
- 2nd retry: Wait 2 seconds
- Then move to next provider

---

## Error Handling

### **All Providers Failed?**

Returns **HTTP 502** (Bad Gateway) with details:

```json
{
  "detail": "Unable to extract text from image. All OCR providers failed:\nGemini: API key not set\nGoogle Vision: Credentials file not found\nTrOCR: Model download failed"
}
```

### **Why 502?**

- 502 = Gateway Error = upstream service(s) unavailable
- Indicates retry might help later
- Distinct from 500 (server error) or 503 (service unavailable)

---

## Configuration Matrix

| Provider | Env Var | Type | Required | Speed | Accuracy |
|----------|---------|------|----------|-------|----------|
| **Gemini** | `GEMINI_API_KEY` | API Key | Optional* | ⚡ Fast | 🎯 Good |
| **Google Vision** | `GOOGLE_APPLICATION_CREDENTIALS` | File Path | Optional* | 🟡 Medium | 🎯 Excellent |
| **TrOCR** | None | Installed Package | Optional | 🐢 Slow | 🎯 Good |

*At least one should be configured for the service to work

---

## Code Examples

### **Using the OCR Fallback**

```python
from app.services.vision_ocr import extract_text_from_image

# Just call this - fallback is automatic!
image_bytes = open("prescription.jpg", "rb").read()
text = extract_text_from_image(image_bytes)  # Returns text from 1st successful provider
```

### **Direct Provider Usage** (Advanced)

```python
from app.services.gemini_ocr import extract_text_with_gemini
from app.services.google_vision_ocr import extract_text_from_image as google_ocr
from app.services.trocr_service import extract_text_with_trocr

# If you want to use specific provider:
text = extract_text_with_gemini(image_bytes)      # Tier 1
text = google_ocr(image_bytes)                    # Tier 2
text = extract_text_with_trocr(image_bytes)       # Tier 3
```

---

## Logging

### **What You'll See**

```
INFO: 🤖 Attempting OCR with Gemini 3.0 Flash (Primary)...
INFO: ✅ Gemini succeeded. Extracted 1523 characters.
```

Or if it fails:

```
WARNING: ❌ Gemini failed: GEMINI_API_KEY not set
WARNING: 🔍 Attempting OCR with Google Cloud Vision (Secondary)...
INFO: ✅ Google Vision succeeded. Extracted 1523 characters.
```

Or if all fail:

```
ERROR: 🚨 All OCR providers failed: Gemini: API timeout | Google Vision: Credentials not found | TrOCR: CUDA out of memory
```

---

## Troubleshooting

### **Issue: "GEMINI_API_KEY not configured"**
```bash
# Fix: Add to .env
GEMINI_API_KEY=your_actual_key
```

### **Issue: "Google credentials file not found"**
```bash
# Fix: Verify path in .env (use absolute path)
GOOGLE_APPLICATION_CREDENTIALS=C:\\Users\\hulkh\\Downloads\\medvault-484813-8de70701326c.json
```

### **Issue: "TrOCR model download failed"**
```bash
# Fix: Pre-download the model
python -c "from transformers import TrOCRProcessor; TrOCRProcessor.from_pretrained('microsoft/trocr-base-handwritten')"
```

### **Issue: "HTTP 502 - All providers failed"**
```bash
# Check:
1. Is internet connection working?
2. Are all API keys valid? (Check Gemini/OpenRouter dashboards)
3. Are rate limits exceeded? (Check API dashboards)
4. Are credentials file accessible? (Check file permissions)
5. All packages installed? (Run: pip install -r requirements.txt)
```

---

## Architecture Comparison

### **OCR Fallback (NEW)**
```
Gemini (API) → Google Vision (API) → TrOCR (Local)
 Fast       →  Accurate          → Reliable
```

### **LLM Fallback (UNCHANGED)**
```
Anthropic → OpenRouter → Groq
(All cloud-based, no changes)
```

**Key Point:** These are independent! Changing OCR fallback doesn't affect LLM fallback.

---

## Files Modified

| File | Change |
|------|--------|
| `app/services/vision_ocr.py` | ✅ Reordered to: Gemini → Google Vision → TrOCR |
| `app/api/ocr.py` | ✅ Updated comments to show new priority |
| `app/core/config.py` | ✅ No changes (already had all required env vars) |
| `app/services/claude_chat.py` | ✅ **No changes** (LLM fallback untouched) |

---

## Performance Notes

### **Typical Response Times**
- **Gemini Success:** ~1-2 seconds ⚡
- **Google Vision Success:** ~3-5 seconds 🟡
- **TrOCR Success:** ~10-20 seconds 🐢
- **All Fail:** ~30-40 seconds (due to retries) 🚨

### **Cost Per Request**
- **Gemini:** $0.000075 ✅
- **Google Vision:** $0.0015 ⚠️
- **TrOCR:** $0.00 ✅

---

## Links

- 📖 [Full Architecture Guide](OCR_FALLBACK_ARCHITECTURE.md)
- 💬 [LLM Fallback Guide](CHAT_FALLBACK_GUIDE.md)
- ⚙️ [Configuration Guide](../app/core/config.py)
- 🔍 [OCR Services](../app/services/)

---

## Summary

✅ **OCR providers now in order:** Gemini → Google Vision → TrOCR  
✅ **Automatic fallback** when provider fails  
✅ **Retry logic** with exponential backoff  
✅ **Clear error messages** showing what failed  
✅ **LLM fallback untouched** (Anthropic → OpenRouter → Groq)  
✅ **Backward compatible** with existing code  

**Status:** 🟢 Ready to use!
