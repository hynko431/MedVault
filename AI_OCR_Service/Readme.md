# AI OCR Service - Quick Start Guide 🚀

Complete setup and usage guide for the MedVault AI OCR & Search Service.

## 📋 Table of Contents

- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Running the Service](#running-the-service)
- [Testing](#testing)
- [API Documentation](#api-documentation)
- [Elasticsearch Setup](#elasticsearch-setup)
- [Troubleshooting](#troubleshooting)
- [Development Workflow](#development-workflow)

---

## ✅ Prerequisites

### Required

- **Python 3.8+** - Check version: `python --version`
- **pip** - Python package manager
- **Google Cloud Vision API Credentials** - JSON key file
- **At least one AI Provider API Key:**
  - Anthropic Claude API key (recommended)
  - OR OpenRouter API key
  - OR Groq API key

### Optional (for full features)

- **Elasticsearch 7.x or 8.x** - For search functionality
- **Docker** - For running Elasticsearch locally

---

## 🔧 Installation

### Step 1: Activate the .venv & Navigate to Service Directory

```bash
C:/Users/hulkh/anaconda3/Scripts/activate
conda activate MedVault 
 C:/Users/hulkh/Downloads/ai_ocr_service/.venv/Scripts/Activate.ps1
cd AI_OCR_Service
```

### Step 2: Install Python Dependencies

```bash
pip install -r requirements.txt
```

**Installed packages:**
- `fastapi` - Web framework
- `uvicorn` - ASGI server
- `pydantic` - Data validation
- `requests` - HTTP client
- `python-dotenv` - Environment management
- `google-cloud-vision` - OCR API client
- `elasticsearch` - Search engine client
- `requests` - getting requests
- `logging` - adding logs in the terminal for the error analysis
- `Pillow` - Image library
- `transformers` - For Importing models
- `torch` - DL Framework
- `google-genai` - Google SDK for importing Latest Libraries

### Step 3: Verify Installation

```bash
python -c "import fastapi; print(f'FastAPI: {fastapi.__version__}')"
python -c "import google.cloud.vision; print('Google Vision: OK')"
```

---

## ⚙️ Configuration

### Step 1: Create Environment File

```bash
# Copy example file
cp .env.example .env

# Edit with your credentials
# Windows: notepad .env
# Mac/Linux: nano .env
```

### Step 2: Configure Required Variables

Open `.env` and set these required variables:

```bash
# ========================================
# REQUIRED: Google Cloud Vision OCR
# ========================================
GOOGLE_APPLICATION_CREDENTIALS="C:\path\to\your\credentials.json"

# ========================================
# REQUIRED: AI Provider (at least one)
# ========================================

# Option 1: Anthropic Claude (Recommended - Best Quality)
ANTHROPIC_API_KEY="sk-ant-api03-YOUR_KEY_HERE"

# Option 2: OpenRouter (Good Availability)
OPENROUTER_API_KEY="sk-or-v1-YOUR_KEY_HERE"

# Option 3: Groq (Fast Inference)
GROQ_API_KEY="gsk_YOUR_KEY_HERE"
```

### Step 3: Configure Optional Variables

```bash
# ========================================
# OPTIONAL: Elasticsearch (for search)
# ========================================
ELASTICSEARCH_ENABLED=false  # Set to true to enable
ELASTICSEARCH_HOST="http://localhost:9200"
```

### Configuration Notes

✅ **Use absolute paths** for `GOOGLE_APPLICATION_CREDENTIALS`  
✅ **Never commit** `.env` file to git (already in `.gitignore`)  
✅ **Multiple AI providers** recommended for fallback capability  
✅ **Elasticsearch** is optional but recommended for search features

---

## 🚀 Running the Service

### Method 1: Development Mode (Recommended)

```bash
python -m uvicorn app.main:app --reload
```

**Features:**
- Auto-reload on code changes
- Runs on `http://localhost:8000`
- Detailed error messages

### Method 2: Production Mode

```bash
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

**Features:**
- Multiple worker processes
- Optimized performance
- Listens on all interfaces

### Method 3: Direct Execution

```bash
python -m app.main
```

### Expected Output

```
INFO:     Started server process [12345]
INFO:     Waiting for application startup.
INFO:     Starting up AI OCR & Search Service...
INFO:     Elasticsearch index initialized successfully
INFO:     Application startup complete.
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
```

---

## 🧪 Testing

### Test 1: Health Check

**Browser Method:**

Open in browser:
```
http://127.0.0.1:8000/health
```

**Expected Response:**
```json
{
  "status": "ok",
  "service": "ai-ocr-search",
  "config": {
    "google_creds_set": true,
    "elasticsearch_enabled": false,
    "providers": {
      "anthropic": {
        "enabled": true,
        "preview": "sk-ant-...QAAA",
        "model": "claude-3-5-sonnet-20240620"
      },
      "openrouter": {
        "enabled": false,
        "preview": null,
        "model": "google/gemma-3-27b-it:free"
      },
      "groq": {
        "enabled": false,
        "preview": null,
        "model": "openai/gpt-oss-120b"
      }
    }
  }
}
```

**Command Line Method:**

```bash
curl http://127.0.0.1:8000/health
```

### Test 2: Interactive API Documentation

Open Swagger UI:
```
http://127.0.0.1:8000/docs
```

**Features:**
- Interactive API testing
- Request/response examples
- Schema documentation
- Try it out functionality

### Test 3: OCR Extraction

**Using Swagger UI:**

1. Navigate to `http://127.0.0.1:8000/docs`
2. Click on **POST /ocr/extract**
3. Click **"Try it out"**
4. Enter request body:
   ```json
   {
     "prescription_id": "test_001",
     "image_url": "YOUR_S3_OR_PUBLIC_IMAGE_URL"
   }
   ```
5. Click **"Execute"**

**Using curl:**

```bash
curl -X POST "http://127.0.0.1:8000/ocr/extract" \
  -H "Content-Type: application/json" \
  -d '{
    "prescription_id": "test_001",
    "image_url": "https://your-s3-bucket.com/prescription.jpg"
  }'
```

**Expected Response (3-8 seconds):**

```json
{
  "prescription_id": "test_001",
  "structured_data": {
    "doctor_name": "Dr. John Smith",
    "hospital": "City Hospital",
    "date": "2024-01-15",
    "patient_name": "Jane Doe",
    "diagnosis": "Upper Respiratory Infection",
    "medicines": [
      {
        "name": "Paracetamol",
        "dosage": "500mg",
        "frequency": "3 times daily",
        "duration": "5 days",
        "instructions": "Take after meals"
      }
    ],
    "tests_advised": ["Blood Test"],
    "follow_up": "7 days"
  }
}
```

### Test 4: Medicine Chat

```bash
curl -X POST "http://127.0.0.1:8000/chat/medicine-chat" \
  -H "Content-Type: application/json" \
  -d '{"question": "What is paracetamol used for?"}'
```

**Expected Response:**

```json
{
  "answer": "Paracetamol is a common pain reliever and fever reducer...",
  "disclaimer": "This information is for educational purposes only...",
  "status": "success"
}
```

---

## 🔍 API Documentation

### OCR Extraction Endpoint

**POST** `/ocr/extract`

Extract structured prescription data from images.

**Request Schema:**
```json
{
  "prescription_id": "string (required)",
  "image_url": "string (required, valid HTTP/HTTPS URL)"
}
```

**Response Schema:**
```json
{
  "prescription_id": "string",
  "structured_data": {
    "doctor_name": "string | null",
    "hospital": "string | null",
    "date": "string | null",
    "patient_name": "string | null",
    "diagnosis": "string | null",
    "medicines": [
      {
        "name": "string | null",
        "dosage": "string | null",
        "frequency": "string | null",
        "duration": "string | null",
        "instructions": "string | null"
      }
    ],
    "tests_advised": ["string"],
    "follow_up": "string | null"
  }
}
```

**Processing Pipeline:**

```
Image URL → Download → Google Vision OCR → Clean Text → 
AI Extraction (Fallback Chain) → JSON Validation → 
Return Response + Background Indexing
```

**Error Codes:**

- `400` - Invalid image URL or no text extracted
- `502` - Google Vision API error (check credentials)
- `503` - All AI providers failed
- `500` - Unexpected server error

### Search Endpoints

Available when `ELASTICSEARCH_ENABLED=true`

**GET** `/search/all`
- Universal search with multi-layer relevance
- Parameters: `q`, `user_id`, `page`, `page_size`, `sort_by`

**GET** `/search/autocomplete`
- Fast prefix matching
- Parameters: `q`, `user_id`, `size`

**GET** `/search/fuzzy`
- Typo-tolerant search
- Parameters: `q`, `user_id`, `page`, `page_size`

**GET** `/search/medicine`
- Medicine-specific search
- Parameters: `q`, `user_id`, `size`

**GET** `/search/provider`
- Doctor/hospital search
- Parameters: `q`, `user_id`, `size`

**GET** `/search/date-range`
- Date-filtered search
- Parameters: `q`, `user_id`, `start_date`, `end_date`

### Medicine Chat Endpoint

**POST** `/chat/medicine-chat`

Ask medicine-related questions.

**Request:**
```json
{
  "question": "string (required)"
}
```

**Response:**
```json
{
  "answer": "string",
  "disclaimer": "string",
  "status": "success"
}
```

---

## 🔍 Elasticsearch Setup

### Option 1: Docker (Recommended)

**Start Elasticsearch:**

```bash
docker run -d \
  --name elasticsearch \
  -p 9200:9200 \
  -p 9300:9300 \
  -e "discovery.type=single-node" \
  -e "xpack.security.enabled=false" \
  docker.elastic.co/elasticsearch/elasticsearch:8.11.0
```

**Verify Elasticsearch:**

```bash
curl http://localhost:9200/_cluster/health
```

**Expected Response:**
```json
{
  "cluster_name": "docker-cluster",
  "status": "green",
  "number_of_nodes": 1
}
```

### Option 2: Manual Installation

1. Download from https://www.elastic.co/downloads/elasticsearch
2. Extract and run: `bin/elasticsearch` (Unix) or `bin\elasticsearch.bat` (Windows)
3. Verify at http://localhost:9200

### Enable Elasticsearch in Service

1. Edit `.env`:
   ```bash
   ELASTICSEARCH_ENABLED=true
   ELASTICSEARCH_HOST="http://localhost:9200"
   ```

2. Restart the service

3. Index will be auto-created on startup

### Migration & Reindexing

**Enable dual-write mode:**

```bash
# Windows (Command Prompt)
set ES_MIGRATION_MODE=true
set NEW_ES_INDEX=prescriptions_v2

# Windows (PowerShell)
$env:ES_MIGRATION_MODE="true"
$env:NEW_ES_INDEX="prescriptions_v2"

# Mac/Linux
export ES_MIGRATION_MODE=true
export NEW_ES_INDEX=prescriptions_v2
```

**Run reindexing script:**

```bash
python scripts/reindex_prescriptions.py
```

**Switch to new index:**

```bash
# Update .env or use alias management
curl -X POST "http://localhost:9200/_aliases" \
  -H 'Content-Type: application/json' \
  -d '{
    "actions": [
      {"remove": {"index": "prescriptions_v1", "alias": "prescriptions_current"}},
      {"add": {"index": "prescriptions_v2", "alias": "prescriptions_current"}}
    ]
  }'
```

---

## 🐛 Troubleshooting

### Issue 1: Service Won't Start

**Error:** `ModuleNotFoundError: No module named 'fastapi'`

**Solution:**
```bash
pip install -r requirements.txt
```

---

### Issue 2: Health Check Shows Providers Disabled

**Error:** All providers show `"enabled": false`

**Solution:**
1. Check `.env` file exists in `AI_OCR_Service` directory
2. Verify API keys are properly formatted (no extra spaces/quotes)
3. Restart the service

**Verify configuration:**
```bash
python -c "from dotenv import load_dotenv; import os; load_dotenv(); print(f'Anthropic: {bool(os.getenv(\"ANTHROPIC_API_KEY\"))}')"
```

---

### Issue 3: 502 Error on OCR Extraction

**Error:** `502 Bad Gateway - Google Vision credentials not found`

**Solution:**

1. **Verify credentials file exists:**
   ```bash
   # Check file path in .env
   type .env | findstr GOOGLE_APPLICATION_CREDENTIALS
   
   # Verify file exists
   dir "C:\path\to\credentials.json"
   ```

2. **Use absolute path:**
   ```bash
   # Wrong (relative path)
   GOOGLE_APPLICATION_CREDENTIALS="./credentials.json"
   
   # Correct (absolute path)
   GOOGLE_APPLICATION_CREDENTIALS="C:\Users\YourName\path\to\credentials.json"
   ```

3. **Test credentials:**
   ```bash
   python -c "from google.cloud import vision; client = vision.ImageAnnotatorClient(); print('✅ Credentials OK')"
   ```

---

### Issue 4: OCR Extraction Times Out

**Error:** Request takes too long or times out

**Possible Causes:**
- Large image files
- Slow network connection
- All AI providers timing out

**Solutions:**

1. **Optimize image size:**
   - Recommended: < 5MB
   - Max resolution: 4096 x 4096

2. **Check AI provider status:**
   ```bash
   curl http://127.0.0.1:8000/health
   # Verify at least one provider is enabled
   ```

3. **Test providers individually:**
   - Anthropic: https://status.anthropic.com
   - OpenRouter: https://status.openrouter.ai
   - Groq: https://status.groq.com

---

### Issue 5: Elasticsearch Connection Failed

**Error:** `Failed to initialize Elasticsearch index`

**Solution:**

1. **Check Elasticsearch is running:**
   ```bash
   curl http://localhost:9200/_cluster/health
   ```

2. **Verify connection string:**
   ```bash
   # .env file
   ELASTICSEARCH_HOST="http://localhost:9200"  # Note: http not https
   ```

3. **Service continues without Elasticsearch:**
   - OCR extraction still works
   - Search endpoints will fail
   - No background indexing

---

### Issue 6: Image Download Fails

**Error:** `400 - Image download failed`

**Causes:**
- Invalid URL format
- URL requires authentication
- Network/firewall issues
- Image file corrupted

**Solutions:**

1. **Verify URL is publicly accessible:**
   ```bash
   curl -I "YOUR_IMAGE_URL"
   # Should return 200 OK
   ```

2. **Use signed URLs for S3:**
   - Generate pre-signed URL with expiration
   - Ensure URL doesn't contain authentication headers

3. **Test with sample image:**
   ```bash
   # Use a public test image
   curl -X POST "http://localhost:8000/ocr/extract" \
     -H "Content-Type: application/json" \
     -d '{
       "prescription_id": "test",
       "image_url": "https://example.com/sample-prescription.jpg"
     }'
   ```

---

## 💻 Development Workflow

### Project Structure

```
AI_OCR_Service/
├── app/
│   ├── __init__.py
│   ├── main.py                    # FastAPI app + startup
│   ├── api/
│   │   ├── ocr.py                # OCR extraction endpoint
│   │   ├── search.py             # Search endpoints
│   │   └── chat.py               # Medicine chat endpoint
│   ├── services/
│   │   ├── image_downloader.py   # Download images from URLs
│   │   ├── google_vision_ocr.py  # Google Vision OCR wrapper
│   │   ├── ocr_cleaner.py        # Text cleaning pipeline
│   │   ├── claude_extractor.py   # AI extraction with fallback
│   │   ├── claude_chat.py        # Medicine chat with fallback
│   │   ├── search_indexer.py     # Elasticsearch indexing
│   │   └── ai_prep.py            # AI text preparation
│   ├── models/
│   │   └── schemas.py            # Pydantic models
│   └── core/
│       ├── config.py             # Settings & environment
│       ├── logger.py             # Logging configuration
│       └── disclaimer.py         # Medical disclaimer text
├── scripts/
│   └── reindex_prescriptions.py  # Elasticsearch reindexing
├── .env                          # Environment variables (gitignored)
├── .env.example                  # Example configuration
├── requirements.txt              # Python dependencies
└── Readme.md                     # This file
```

### Code Modification Guide

**To add a new field to extraction:**

1. Update `app/models/schemas.py` - Add field to `PrescriptionExtracted`
2. Update `app/services/claude_extractor.py` - Update AI prompt
3. Update `app/services/search_indexer.py` - Add field to index mapping

**To add a new AI provider:**

1. Update `app/core/config.py` - Add API key settings
2. Update `app/services/claude_extractor.py` - Add provider method
3. Update fallback chain in `extract_structured_data()`

**To modify search relevance:**

1. Edit `app/services/search_indexer.py`
2. Adjust boost values in query construction
3. Test with sample queries

### Logging

**View logs in console:**
- Startup messages
- Request processing
- Provider fallback attempts
- Error details

**Log levels:**
- `INFO` - Normal operations
- `WARNING` - Provider failures (during fallback)
- `ERROR` - Critical failures

**Example log output:**
```
INFO: Attempting OCR extraction with Anthropic...
WARNING: Anthropic failed: Connection timeout
INFO: Falling back to OpenRouter...
INFO: Successfully extracted with OpenRouter
```

---

## 📚 Additional Resources

### Documentation Files

- **[CHAT_FALLBACK_GUIDE.md](CHAT_FALLBACK_GUIDE.md)** - Complete guide to AI provider fallback mechanism
- **[ELASTICSEARCH_SEARCH_GUIDE.md](ELASTICSEARCH_SEARCH_GUIDE.md)** - Deep dive into search implementation
- **[SEARCH_CHEAT_SHEET.md](SEARCH_CHEAT_SHEET.md)** - Quick reference for search features

### External Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Google Cloud Vision API](https://cloud.google.com/vision/docs)
- [Anthropic Claude API](https://docs.anthropic.com/)
- [Elasticsearch Documentation](https://www.elastic.co/guide/)

---

## 🎯 Quick Reference

### Essential Commands

```bash
# Start development server
python -m uvicorn app.main:app --reload

# Run with specific port
python -m uvicorn app.main:app --port 8080

# Check health
curl http://localhost:8000/health

# Open Swagger UI
# Browser: http://localhost:8000/docs

# Test OCR
curl -X POST http://localhost:8000/ocr/extract \
  -H "Content-Type: application/json" \
  -d '{"prescription_id":"test","image_url":"YOUR_URL"}'

# Test chat
curl -X POST http://localhost:8000/chat/medicine-chat \
  -H "Content-Type: application/json" \
  -d '{"question":"What is aspirin?"}'
```

### Environment Variables Checklist

```bash
✅ GOOGLE_APPLICATION_CREDENTIALS  # Required
✅ ANTHROPIC_API_KEY               # Recommended
☑️ OPENROUTER_API_KEY              # Optional (fallback)
☑️ GROQ_API_KEY                    # Optional (fallback)
☑️ ELASTICSEARCH_ENABLED           # Optional (default: false)
☑️ ELASTICSEARCH_HOST              # Optional (default: http://localhost:9200)
```

---

## 🔄 End-to-End Flow Summary

```
Prescription Image
        ↓
OCR Engine (Google Vision OCR API)
        ↓
Text Cleaning Pipeline
        ↓
AI Extraction (Anthropic → OpenRouter → Groq)
        ↓
JSON Validation (Pydantic)
        ↓
Structured Response + Background Indexing
```

---

## ✅ Success Indicators

Your service is properly configured when:

✅ Health endpoint returns `"status": "ok"`  
✅ At least one provider shows `"enabled": true`  
✅ Google credentials show `"google_creds_set": true`  
✅ Swagger UI loads at `/docs`  
✅ OCR extraction returns structured data  
✅ Response time is 3-8 seconds for OCR  
✅ Medicine chat returns answers in 1-3 seconds  

---

**Need help?** Check the troubleshooting section or refer to the comprehensive guides in the documentation folder.

**Ready to deploy?** See the main project README for production deployment guidelines.
