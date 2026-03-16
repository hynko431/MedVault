# OCR API Endpoint - Backend Integration Guide

## Overview

The AI OCR Service now exposes a **RESTful API endpoint** (`POST /ocr/extract`) that your backend can call to extract prescription data from images. This approach provides **complete separation of concerns** - the service handles all credential management internally, and your backend simply receives the extracted data.

## Key Feature: No Direct Service Account Usage

As per your requirement, your backend code does **NOT** need:

- ❌ Google Cloud service account credentials
- ❌ Gemini API keys
- ❌ Direct access to LLM providers
- ❌ Knowledge of OCR implementation details

Your backend only needs:

- ✅ The endpoint URL: `http://127.0.0.1:8000/ocr/extract`
- ✅ Request payload with prescription ID and image URL
- ✅ HTTP client library (requests, httpx, fetch, etc.)

---

## Starting the Service

### Option 1: Manual Start (Development)

```bash
cd AI_OCR_Service
set PYTHONPATH=.
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

### Option 2: Background Process (Windows)

```bash
cd AI_OCR_Service
set PYTHONPATH=.
start python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

### Option 3: Using Batch File

Create `start_ocr_service.bat`:

```batch
@echo off
cd /d "C:\Users\hulkh\Downloads\ai_ocr_service\AI_OCR_Service"
set PYTHONPATH=.
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
pause
```

---

## API Endpoint Reference

### POST /ocr/extract

**Purpose:** Extract prescription data from an image

**URL:** `http://127.0.0.1:8000/ocr/extract`

**Request Headers:**

```
Content-Type: application/json
```

**Request Body:**

```json
{
  "prescription_id": "RX-12345",
  "image_url": "https://example.com/prescription-image.jpg",
  "user_id": "user-001"
}
```

**Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `prescription_id` | string | Yes | Unique identifier for the prescription |
| `image_url` | string | Yes | URL to the prescription image to process |
| `user_id` | string | No | Optional user identifier for audit/filtering |

**Response (Success - 200):**

```json
{
  "prescription_id": "RX-12345",
  "ocr_text": "Dr. John Smith\nPrescription for Patient\nMedicine 1...",
  "extracted_data": {
    "doctor_name": "Dr. John Smith",
    "hospital": "City Medical Center",
    "patient_name": "John Doe",
    "medicines": [
      {
        "name": "Aspirin",
        "dosage": "500mg",
        "frequency": "Once daily",
        "duration": "10 days"
      },
      {
        "name": "Paracetamol",
        "dosage": "1000mg",
        "frequency": "Twice daily",
        "duration": "5 days"
      }
    ]
  },
  "processing_time_ms": 2340,
  "ocr_provider_used": "google_vision"
}
```

**Response (Error - 502):**

```json
{
  "detail": "Unable to extract text from image. All OCR providers failed: [error details]"
}
```

---

## Backend Integration Examples

### Python - Using `requests` Library

```python
import requests
import json

def extract_prescription(prescription_id, image_url, user_id=None):
    """
    Call the OCR API to extract prescription data.
    This is how your backend calls the service - no credentials needed!
    """
    
    payload = {
        "prescription_id": prescription_id,
        "image_url": image_url
    }
    
    if user_id:
        payload["user_id"] = user_id
    
    try:
        response = requests.post(
            "http://127.0.0.1:8000/ocr/extract",
            json=payload,
            timeout=120  # 2 minutes for processing
        )
        
        if response.status_code == 200:
            extracted_data = response.json()
            
            # Store in your database
            save_to_db({
                "prescription_id": extracted_data["prescription_id"],
                "ocr_text": extracted_data["ocr_text"],
                "extracted_data": extracted_data["extracted_data"],
                "ocr_provider": extracted_data["ocr_provider_used"]
            })
            
            return extracted_data
        else:
            handle_error(response.json())
            return None
    
    except requests.exceptions.Timeout:
        print("OCR processing timeout - image may be too large or complex")
    except requests.exceptions.ConnectionError:
        print("Cannot connect to OCR service - ensure it's running")

# Usage
result = extract_prescription(
    prescription_id="RX-001",
    image_url="https://example.com/prescription.jpg",
    user_id="patient-123"
)
```

### Python - Using `httpx` (Async)

```python
import httpx

async def extract_prescription_async(prescription_id, image_url):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://127.0.0.1:8000/ocr/extract",
            json={
                "prescription_id": prescription_id,
                "image_url": image_url
            },
            timeout=120
        )
        return response.json() if response.status_code == 200 else None
```

### Node.js - Using `axios`

```javascript
const axios = require('axios');

async function extractPrescription(prescriptionId, imageUrl, userId) {
    try {
        const response = await axios.post(
            'http://127.0.0.1:8000/ocr/extract',
            {
                prescription_id: prescriptionId,
                image_url: imageUrl,
                user_id: userId
            },
            { timeout: 120000 } // 2 minutes
        );
        
        const extractedData = response.data;
        
        // Store in your database
        await saveToDatabase({
            prescription_id: extractedData.prescription_id,
            ocr_text: extractedData.ocr_text,
            extracted_data: extractedData.extracted_data,
            ocr_provider: extractedData.ocr_provider_used
        });
        
        return extractedData;
    } catch (error) {
        console.error('OCR extraction failed:', error.message);
        return null;
    }
}
```

### JavaScript (Browser Fetch)

```javascript
async function extractPrescription(prescriptionId, imageUrl) {
    try {
        const response = await fetch('http://127.0.0.1:8000/ocr/extract', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                prescription_id: prescriptionId,
                image_url: imageUrl
            })
        });
        
        if (!response.ok) {
            throw new Error(`OCR extraction failed: ${response.statusText}`);
        }
        
        const extractedData = await response.json();
        
        // Store in your database/backend
        return extractedData;
    } catch (error) {
        console.error('Error:', error);
        return null;
    }
}
```

### C# / .NET

```csharp
using System;
using System.Net.Http;
using System.Threading.Tasks;
using Newtonsoft.Json;

public class OcrClient
{
    private readonly HttpClient _httpClient;
    private const string OcrServiceUrl = "http://127.0.0.1:8000/ocr/extract";
    
    public OcrClient(HttpClient httpClient)
    {
        _httpClient = httpClient;
    }
    
    public async Task<ExtractedPrescriptionData> ExtractPrescriptionAsync(
        string prescriptionId, 
        string imageUrl,
        string userId = null)
    {
        var payload = new
        {
            prescription_id = prescriptionId,
            image_url = imageUrl,
            user_id = userId
        };
        
        var content = new StringContent(
            JsonConvert.SerializeObject(payload),
            System.Text.Encoding.UTF8,
            "application/json"
        );
        
        try
        {
            var response = await _httpClient.PostAsync(
                OcrServiceUrl,
                content
            );
            
            if (response.IsSuccessStatusCode)
            {
                var json = await response.Content.ReadAsStringAsync();
                return JsonConvert.DeserializeObject<ExtractedPrescriptionData>(json);
            }
            else
            {
                Console.WriteLine($"OCR extraction failed: {response.StatusCode}");
                return null;
            }
        }
        catch (HttpRequestException ex)
        {
            Console.WriteLine($"Connection error: {ex.Message}");
            return null;
        }
    }
}

// Usage
var client = new OcrClient(new HttpClient { Timeout = TimeSpan.FromMinutes(2) });
var result = await client.ExtractPrescriptionAsync("RX-001", "https://example.com/prescription.jpg");
```

---

## Architecture Benefits

### 1. **Separation of Concerns**

- ✅ OCR Service manages all API credentials
- ✅ Backend only calls a simple HTTP endpoint
- ✅ Credentials never distributed to multiple services

### 2. **Security**

- ✅ Service account credentials in one secure location
- ✅ Reduced attack surface (fewer places with credentials)
- ✅ Easier credential rotation
- ✅ Audit logging in one place

### 3. **Scalability**

- ✅ Backend can be horizontally scaled without credential management
- ✅ OCR Service can be scaled/updated independently
- ✅ Load balancing across multiple OCR instances (future)

### 4. **Resilience**

- ✅ Multi-provider fallback (Gemini → Google Vision → PaddleOCR-VL)
- ✅ Automatic retries with exponential backoff
- ✅ Provider failures don't affect backend code
- ✅ Service handles timeouts internally

### 5. **Monitoring**

- ✅ All OCR operations logged in one place
- ✅ Easy to track which provider succeeded
- ✅ Performance metrics available at service level

---

## API Documentation (Interactive)

Once the service is running, you can access:

1. **Swagger UI:** `http://127.0.0.1:8000/docs`
   - Interactive API testing
   - Request/response examples
   - Try out endpoints directly

2. **ReDoc:** `http://127.0.0.1:8000/redoc`
   - Read-only API documentation
   - Clean, organized layout

3. **OpenAPI Schema:** `http://127.0.0.1:8000/openapi.json`
   - Machine-readable API specification
   - Use for code generation tools

---

## OCR Provider Fallback Chain

The service automatically uses multiple OCR providers in this order:

### 1. **Google Gemini 1.5 Flash (Primary)**

- Uses vision-language model
- Good for handwritten text
- Timeout: 60 seconds

### 2. **Google Cloud Vision (Secondary)**

- Fallback if Gemini fails
- Highest accuracy
- Fast processing
- Handles complex documents
- Timeout: 60 seconds

### 3. **PaddleOCR-VL (Tertiary)**

- Local transformer-based OCR
- No API calls, runs locally
- Slower but reliable fallback
- Timeout: 120 seconds

**Result:** Service is resilient to provider outages. If Gemini fails, it automatically tries Google Vision, then PaddleOCR-VL.

---

## Error Handling

### Common Errors and Solutions

| Status | Error | Solution |
|--------|-------|----------|
| 502 | All OCR providers failed | Check image URL is accessible, try with different image |
| 422 | Validation error | Ensure `prescription_id` and `image_url` are provided |
| 504 | Gateway timeout | Image processing taking too long, try with simpler image |
| Connection refused | Service not running | Start service: `python -m uvicorn app.main:app` |

### Retry Strategy for Backend

```python
import time
from requests.exceptions import RequestException

def extract_with_retry(prescription_id, image_url, max_retries=3):
    for attempt in range(max_retries):
        try:
            response = requests.post(
                "http://127.0.0.1:8000/ocr/extract",
                json={"prescription_id": prescription_id, "image_url": image_url},
                timeout=120
            )
            
            if response.status_code == 200:
                return response.json()
            elif response.status_code >= 500:
                # Server error, retry
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt  # Exponential backoff
                    print(f"Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                    continue
            else:
                # Client error, don't retry
                break
        
        except RequestException as e:
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt
                print(f"Connection error, retrying in {wait_time} seconds...")
                time.sleep(wait_time)
            else:
                raise
    
    return None
```

---

## Testing Your Integration

### Test 1: Health Check

```bash
curl http://127.0.0.1:8000/health
```

### Test 2: Extract from Sample Image

```bash
curl -X POST http://127.0.0.1:8000/ocr/extract \
  -H "Content-Type: application/json" \
  -d '{"prescription_id":"TEST-001","image_url":"https://via.placeholder.com/400x300"}'
```

### Test 3: Run Python Test Script

```bash
python test_ocr_endpoint.py
```

---

## Production Deployment Checklist

- [ ] Verify all API keys in `.env` are valid
- [ ] Test OCR extraction with real prescription images
- [ ] Set up error logging/monitoring
- [ ] Configure appropriate timeout values for your use case
- [ ] Test fallback behavior (disable one provider temporarily)
- [ ] Set up auto-restart (systemd service, Docker, etc.)
- [ ] Monitor service health regularly
- [ ] Document internal IP/port for backend access
- [ ] Set up credentials rotation schedule
- [ ] Test backup/recovery procedures

---

## Summary

Your backend now:

1. ✅ Calls `/ocr/extract` endpoint (no credentials needed)
2. ✅ Receives extracted prescription data
3. ✅ Stores results in your database
4. ✅ Has automatic fallback and retry protection
5. ✅ Benefits from centralized credential management

The OCR Service handles all the complexity - credential management, API calls, retries, fallbacks, and error handling - leaving your backend code simple and focused on business logic.
