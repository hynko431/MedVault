# 🐛 AI OCR Service - Debugging Guide

## Overview of Fixes Implemented

This document explains the issues that were causing the **502 Bad Gateway** error and the comprehensive fixes that have been implemented.

---

## 🔴 Root Causes & Solutions

### 1. **Missing OCR Fallback Pipeline** ✅ FIXED

**Problem:**
- Only Google Cloud Vision was being used for OCR
- No fallback mechanism if credentials were missing or API failed
- Single point of failure causing 502 errors

**Solution:**
- Created `vision_ocr.py` with intelligent fallback pipeline
- **Priority Chain**: Google Vision → Gemini 3.0 Flash → TrOCR
- Each provider has built-in retry logic with exponential backoff
- Proper error logging at each stage

**How it works:**

```text
OCR Request
    ↓
Try Google Vision (Most Accurate)
    ├─ Success? Return text
    └─ Failed? Try next...
    ↓
Try Gemini 3.0 Flash (API-based Alternative)
    ├─ Success? Return text
    └─ Failed? Try next...
    ↓
Try TrOCR (Local Fallback)
    ├─ Success? Return text
    └─ Failed? Return UnifiedOCRError (502)
```

**Files Modified:**
- `app/services/vision_ocr.py` - New unified OCR pipeline
- `app/api/ocr.py` - Updated imports and error handling

---

### 2. **Synchronous OCR Endpoint** ✅ FIXED

**Problem:**
- `@router.post("/extract")` was synchronous (not `async`)
- Long-running operations blocked the event loop
- Connection timeouts after 30-60 seconds → 502 errors

**Solution:**
- Converted endpoint to async: `async def extract_prescription(...)`
- FastAPI can now handle multiple concurrent requests
- Non-blocking I/O for all network operations

**File Modified:**
- `app/api/ocr.py` - Changed `def` → `async def`

---

### 3. **Missing Extraction Validation** ✅ FIXED

**Problem:**
- `extract_structured_data()` returns `dict`
- `validate_extracted_json()` expected strict format
- Type mismatches could cause silent failures

**Solution:**
- Updated `validate_extracted_json()` to handle both `dict` and `PrescriptionExtracted`
- Added type checking and proper error messages
- Better logging of validation steps

**File Modified:**
- `app/services/claude_extractor.py` - Improved validation function

---

### 4. **No Extraction Provider Fallbacks with Retry Logic** ✅ FIXED

**Problem:**
- Had fallback chain (Anthropic → OpenRouter → Groq) but no retry logic
- Transient failures would immediately fail
- No exponential backoff for rate limiting

**Solution:**
- Added `retry_with_backoff()` decorator to all API calls
- 3 retry attempts with exponential backoff (1s, 2s, 4s delays)
- Smart error handling (don't retry 4xx errors)
- Detailed error context in logs

**Files Modified:**
- `app/services/claude_extractor.py` - Added retry decorator and applied to all providers

---

### 5. **Weak Error Handling & Missing Timeouts** ✅ FIXED

**Problem:**
- Google Vision API calls had no timeout
- No detailed error messages for debugging
- Errors silently swallowed without proper logging

**Solution:**
- All API calls now have explicit `timeout=30s` or `timeout=60s`
- Improved error messages with context (what failed, why, how to fix)
- Added `exc_info=True` to logger.error() for stack traces
- Specific exception types for each service

**Files Modified:**
- `app/services/google_vision_ocr.py` - Added detailed error messages and timeout
- `app/services/gemini_ocr.py` - Added timeout and better error handling
- `app/services/trocr_service.py` - Added timeout handling and better logging
- `app/services/image_downloader.py` - Added timeout and descriptive errors

---

## 🔍 Common Error Scenarios & Solutions

### Scenario 1: `502 Bad Gateway` on OCR Request

**Error in logs:**

```text
ERROR: 🚨 All OCR providers failed:
  - Google Vision: GOOGLE_APPLICATION_CREDENTIALS environment variable not set
  - Gemini: GEMINI_API_KEY not configured
  - TrOCR: TrOCR dependencies not installed
```

**Solutions:**

1. **Missing Google Credentials:**

   ```bash
   # Option A: Add to .env file
   GOOGLE_APPLICATION_CREDENTIALS="C:\path\to\medvault-484813-cf9d74cb47c8.json"
   
   # Option B: Check file path is correct
   ls -la "C:\path\to\medvault-484813-cf9d74cb47c8.json"
   ```

2. **Missing Gemini API Key:**

   ```bash
   # Add to .env file
   GEMINI_API_KEY="your-gemini-api-key-here"
   ```

3. **TrOCR Dependencies:**

   ```bash
   pip install transformers torch pillow
   ```

---

### Scenario 2: `503 Service Unavailable` on Extraction

**Error in logs:**

```text
ERROR: 🚨 All AI extraction providers failed:
  - Anthropic failed: Failed to connect to api.anthropic.com
  - OpenRouter failed: Failed to connect to openrouter.ai/api/v1/chat/completions
  - Groq failed: Failed to connect to api.groq.com
```

**Solutions:**

1. **Check API Keys:**

   ```bash
   # Verify keys are set
   echo $ANTHROPIC_API_KEY
   echo $OPENROUTER_API_KEY
   echo $GROQ_API_KEY
   ```

2. **Check Network Connectivity:**

   ```bash
   curl -I https://api.anthropic.com
   curl -I https://openrouter.ai
   curl -I https://api.groq.com
   ```

3. **Check Rate Limits:**
   - Each provider has rate limits
   - Retry logic will backoff exponentially
   - Wait a few minutes and try again

---

### Scenario 3: Timeout Errors

**Error in logs:**

```text
WARNING: google_vision_extract attempt 1/2 failed. Retrying in 1s... Error: Request timed out after 60s
```

**Solutions:**

1. **Large Images:**
   - Max image size: 5MB
   - Compress image and retry

2. **Network Issues:**
   - Check internet connection
   - Try from a different network
   - Contact your network administrator

3. **Service Degradation:**
   - The API service may be experiencing issues
   - Check provider's status page:
     - Google Cloud: [https://status.cloud.google.com/](https://status.cloud.google.com/)
     - OpenRouter: [https://status.openrouter.dev/](https://status.openrouter.dev/)
     - Anthropic: [https://status.anthropic.com/](https://status.anthropic.com/)
     - Groq: Check their status page

---

### Scenario 4: Image Download Failures

**Error in logs:**

```text
ImageDownloadError: HTTP error downloading image. Status: 403
URL: https://s3.amazonaws.com/...
```

**Solutions:**

1. **403 Forbidden:**

   ```
   - Image URL is expired or doesn't have proper permissions
   - Check S3 bucket policies
   - Check AWS credentials if using AWS SDK
   ```

2. **404 Not Found:**

   ```
   - Image URL is incorrect or image was deleted
   - Verify the URL is correct
   - Check that the image exists in the storage location
   ```

3. **Invalid Content-Type:**

   ```
   - URL doesn't return an image (returns HTML, JSON, etc.)
   - Check that the URL actually points to an image file
   - Verify MIME type is image/* (jpeg, png, gif, webp, etc.)
   ```

---

## 📊 Fallback Mechanisms Reference

### OCR Pipeline (vision_ocr.py)

```text
1. Google Cloud Vision
   - Pros: Most accurate, handles complex layouts
   - Cons: Requires credentials file
   - Timeout: 60s
   - Retries: 2x with 1s, 2s backoff

2. Gemini 3.0 Flash
   - Pros: API-based, no file needed
   - Cons: Slower than Vision
   - Timeout: 60s
   - Retries: 2x with 1s, 2s backoff

3. TrOCR (Local)
   - Pros: Free, no API key, offline
   - Cons: Slower, requires model download (~400MB)
   - Timeout: None (local processing)
   - Retries: 2x
```

### Extraction Pipeline (claude_extractor.py)

```text
1. Anthropic (Claude 3.5 Sonnet)
   - Model: claude-3-5-sonnet-20240620
   - Timeout: 30s
   - Retries: 3x with 1s, 2s, 4s backoff

2. OpenRouter (Anthropic Claude via OpenRouter)
   - Model: anthropic/claude-sonnet-4.5
   - Timeout: 30s
   - Retries: 3x with exponential backoff

3. Groq (Open Source Models)
   - Model: openai/gpt-oss-safeguard-20b
   - Timeout: 30s
   - Retries: 3x with exponential backoff
```

---

## 🔧 Configuration Reference

### .env File Settings

```dotenv
# Google Cloud Vision (Primary OCR)
GOOGLE_APPLICATION_CREDENTIALS="path/to/credentials.json"

# Gemini (Secondary OCR)
GEMINI_API_KEY="your-gemini-api-key"
GEMINI_MODEL="gemini-3-flash"

# Anthropic (Primary Extraction)
ANTHROPIC_API_KEY="your-anthropic-api-key"
ANTHROPIC_MODEL="claude-3-5-sonnet-20240620"

# OpenRouter (Fallback Extraction)
OPENROUTER_API_KEY="your-openrouter-api-key"
OPENROUTER_MODEL="anthropic/claude-sonnet-4.5"

# Groq (Fallback Extraction)
GROQ_API_KEY="your-groq-api-key"
GROQ_MODEL="openai/gpt-oss-safeguard-20b"

# Search (Optional)
ELASTICSEARCH_ENABLED=false
ELASTICSEARCH_HOST="http://localhost:9200"
```

---

## 🧪 Testing the Fixes

### Test 1: Verify OCR Fallback Chain

```bash
# This test will try all OCR providers in sequence
curl -X POST http://localhost:8000/ocr/extract \
  -H "Content-Type: application/json" \
  -d '{
    "prescription_id": "test-123",
    "image_url": "https://example.com/prescription.jpg"
  }'

# Expected: Should try Google Vision, then Gemini, then TrOCR
# Check logs for: "✅ Provider succeeded"
```

### Test 2: Verify Async Endpoint

```bash
# Send multiple concurrent requests
for i in {1..5}; do
  curl -X POST http://localhost:8000/ocr/extract \
    -H "Content-Type: application/json" \
    -d "{\"prescription_id\": \"test-$i\", \"image_url\": \"https://...\"}" &
done
wait

# Expected: All requests handled concurrently (fast)
# Before fix: Would timeout serially (slow)
```

### Test 3: Verify Extraction Fallback

```bash
# Check logs for extraction provider chain
# Should see: Anthropic → OpenRouter → Groq attempts
```

### Test 4: Check Error Messages

```bash
# Test with missing credentials
unset GOOGLE_APPLICATION_CREDENTIALS

curl -X POST http://localhost:8000/ocr/extract \
  -H "Content-Type: application/json" \
  -d '{"prescription_id": "test", "image_url": "https://..."}'

# Expected: Clear error message with helpful troubleshooting steps
```

---

## 📈 Performance Improvements

| Metric | Before | After |
|--------|--------|-------|
| **Single Point of Failure** | Yes (only Google Vision) | No (3 fallback providers) |
| **Timeout on Long Requests** | ~30-60s → 502 | Async handling, no timeout |
| **Transient Failures** | Immediate error | Auto-retry with backoff |
| **Provider Downtime** | Service down | Automatic failover |
| **Concurrent Requests** | Blocked/serialized | Non-blocking/parallel |
| **Error Debugging** | Generic messages | Detailed context & solutions |

---

## 🚀 Next Steps

1. **Monitor logs** for any remaining errors:

   ```bash
   # On Windows
   tail -f uvicorn.log
   
   # On Linux/Mac
   journalctl -u uvicorn -f
   ```

2. **Set up alerting** for 502 errors in production

3. **Configure** all API keys in `.env` for full redundancy

4. **Test failover** by temporarily disabling one provider

5. **Document** any custom errors in your deployment

---

## 📞 Support

If you encounter persistent issues:

1. **Check the logs** - They now contain detailed error context
2. **Look up the error** in this guide
3. **Check provider status** pages (linked above)
4. **Verify credentials** are correct and not expired
5. **Test connectivity** to each provider endpoint

---

## 📝 Summary of Changes

### Files Created

- `app/services/vision_ocr.py` - New unified OCR pipeline with fallbacks

### Files Modified

- `app/api/ocr.py` - Made async, updated imports and error handling
- `app/services/claude_extractor.py` - Added retry logic to all providers
- `app/services/google_vision_ocr.py` - Added timeout and detailed errors
- `app/services/gemini_ocr.py` - Added timeout and better error handling
- `app/services/trocr_service.py` - Added timeout and detailed logging
- `app/services/image_downloader.py` - Added timeout and descriptive errors

### Architecture Changes

- ✅ Synchronous → Async endpoint (non-blocking)
- ✅ Single provider → Multi-provider fallback (resilient)
- ✅ No retry logic → Exponential backoff retries (robust)
- ✅ Generic errors → Detailed contextual errors (debuggable)
