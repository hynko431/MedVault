# Gemini Interactions API - Code Examples

## Basic Usage

### Example 1: Extract Text from Medical Prescription

```python
from app.services.gemini_ocr import extract_text_with_gemini
from PIL import Image
from io import BytesIO

# Load image
image = Image.open("prescription.jpg")
image_bytes = BytesIO()
image.save(image_bytes, format='JPEG')
image_bytes.seek(0)

# Extract text
try:
    extracted_text = extract_text_with_gemini(image_bytes.getvalue())
    print("Extracted Text:")
    print(extracted_text)
except Exception as e:
    print(f"Error: {e}")
```

---

## Advanced Usage

### Example 2: Using Different Gemini Models

```python
import os
from app.services.gemini_ocr import extract_text_with_gemini

# Set your preferred model
os.environ['GEMINI_MODEL'] = 'gemini-3-pro-preview'  # More capable

# Now extract with the new model
extracted_text = extract_text_with_gemini(image_bytes)
print(extracted_text)
```

### Example 3: Using Environment Configuration

```python
# In .env file:
# GEMINI_MODEL=gemini-3-pro-preview
# GEMINI_API_KEY=your_key_here

# In Python:
from app.core.config import settings
from app.services.gemini_ocr import extract_text_with_gemini

print(f"Using model: {settings.GEMINI_MODEL}")
text = extract_text_with_gemini(image_bytes)
```

---

## Integration Examples

### Example 4: FastAPI Endpoint Integration

```python
from fastapi import FastAPI, File, UploadFile
from app.services.gemini_ocr import extract_text_with_gemini

app = FastAPI()

@app.post("/extract-text/")
async def extract_text_endpoint(file: UploadFile = File(...)):
    """Extract text from uploaded image using Gemini"""
    try:
        contents = await file.read()
        extracted_text = extract_text_with_gemini(contents)
        return {
            "success": True,
            "text": extracted_text,
            "length": len(extracted_text)
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }
```

### Example 5: Batch Processing

```python
from pathlib import Path
from app.services.gemini_ocr import extract_text_with_gemini
import logging

logger = logging.getLogger(__name__)

def batch_extract_from_directory(image_dir: str) -> dict:
    """Extract text from all images in a directory"""
    results = {}
    image_dir = Path(image_dir)
    
    for image_file in image_dir.glob("*.jpg"):
        try:
            with open(image_file, "rb") as f:
                image_bytes = f.read()
            
            text = extract_text_with_gemini(image_bytes)
            results[image_file.name] = {
                "success": True,
                "text": text,
                "length": len(text)
            }
            logger.info(f"✅ Processed {image_file.name}")
        except Exception as e:
            results[image_file.name] = {
                "success": False,
                "error": str(e)
            }
            logger.error(f"❌ Failed {image_file.name}: {e}")
    
    return results

# Usage
results = batch_extract_from_directory("./images/prescriptions")
print(results)
```

---

## Error Handling

### Example 6: Comprehensive Error Handling

```python
from app.services.gemini_ocr import extract_text_with_gemini, GeminiOCRError
from google import genai
import logging

logger = logging.getLogger(__name__)

def safe_extract_text(image_bytes: bytes) -> str:
    """Extract text with comprehensive error handling"""
    try:
        return extract_text_with_gemini(image_bytes)
    
    except GeminiOCRError as e:
        logger.error(f"Gemini OCR Error: {e}")
        # Could fallback to another OCR service here
        raise
    
    except genai.APIError as e:
        logger.error(f"API Error: {e}")
        raise
    
    except genai.APIConnectionError as e:
        logger.error(f"Connection Error: {e}")
        # Could retry with exponential backoff
        raise
    
    except TimeoutError as e:
        logger.error(f"Timeout: {e}")
        # Could retry with longer timeout
        raise
    
    except Exception as e:
        logger.error(f"Unexpected Error: {e}", exc_info=True)
        raise

# Usage
try:
    text = safe_extract_text(image_bytes)
except Exception as e:
    print(f"Failed to extract: {e}")
```

---

## Model Selection

### Example 7: Dynamic Model Selection

```python
from app.services.gemini_ocr import (
    extract_text_with_gemini, 
    get_available_gemini_models
)
import os

def select_best_model_for_task(task: str) -> str:
    """Select the best model based on task requirements"""
    models = get_available_gemini_models()
    
    if task == "fast":
        # Prioritize speed
        return "gemini-3-flash-preview"
    elif task == "quality":
        # Prioritize accuracy
        return "gemini-3-pro-preview"
    elif task == "cost":
        # Minimize cost
        return "gemini-2.5-flash-lite"
    else:
        return "gemini-3-flash-preview"  # Default

# Usage
model = select_best_model_for_task("quality")
os.environ['GEMINI_MODEL'] = model
print(f"Using model: {model}")

extracted_text = extract_text_with_gemini(image_bytes)
```

---

## Testing Examples

### Example 8: Unit Test

```python
import pytest
from unittest.mock import patch, MagicMock
from app.services.gemini_ocr import extract_text_with_gemini, GeminiOCRError

@pytest.fixture
def sample_image_bytes():
    """Create sample image bytes"""
    from PIL import Image
    from io import BytesIO
    
    img = Image.new('RGB', (100, 100), color='red')
    bytes_io = BytesIO()
    img.save(bytes_io, format='JPEG')
    bytes_io.seek(0)
    return bytes_io.getvalue()

def test_extract_text_success(sample_image_bytes):
    """Test successful text extraction"""
    with patch('google.genai.Client') as mock_client:
        # Mock the response
        mock_interaction = MagicMock()
        mock_output = MagicMock()
        mock_output.type = "text"
        mock_output.text = "Sample prescription text"
        mock_interaction.outputs = [mock_output]
        
        mock_client_instance = MagicMock()
        mock_client_instance.interactions.create.return_value = mock_interaction
        mock_client.return_value = mock_client_instance
        
        # Test
        result = extract_text_with_gemini(sample_image_bytes)
        assert result == "Sample prescription text"

def test_extract_text_missing_api_key(sample_image_bytes, monkeypatch):
    """Test error handling for missing API key"""
    monkeypatch.setenv("GEMINI_API_KEY", "")
    
    with pytest.raises(GeminiOCRError, match="GEMINI_API_KEY not configured"):
        extract_text_with_gemini(sample_image_bytes)
```

### Example 9: Integration Test

```python
import pytest
from app.services.gemini_ocr import extract_text_with_gemini
from pathlib import Path
import os

@pytest.mark.skipif(
    not os.getenv("GEMINI_API_KEY"),
    reason="GEMINI_API_KEY not set"
)
def test_extract_from_real_image():
    """Integration test with real image (requires API key)"""
    # Use a test image
    test_image_path = Path(__file__).parent / "test_images" / "sample.jpg"
    
    if not test_image_path.exists():
        pytest.skip("Test image not found")
    
    with open(test_image_path, "rb") as f:
        image_bytes = f.read()
    
    # Extract text
    result = extract_text_with_gemini(image_bytes)
    
    # Verify result
    assert isinstance(result, str)
    assert len(result) > 0
    print(f"Extracted: {result[:100]}...")
```

---

## Monitoring and Logging

### Example 10: Performance Monitoring

```python
import time
import logging
from app.services.gemini_ocr import extract_text_with_gemini

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def extract_with_timing(image_bytes: bytes) -> tuple[str, float]:
    """Extract text and log timing information"""
    start_time = time.time()
    
    try:
        text = extract_text_with_gemini(image_bytes)
        elapsed_time = time.time() - start_time
        
        logger.info(f"✅ Extraction completed in {elapsed_time:.2f}s")
        logger.info(f"   Extracted {len(text)} characters")
        
        return text, elapsed_time
    
    except Exception as e:
        elapsed_time = time.time() - start_time
        logger.error(f"❌ Extraction failed after {elapsed_time:.2f}s: {e}")
        raise

# Usage
text, elapsed = extract_with_timing(image_bytes)
print(f"Result: {text[:100]}...")
print(f"Time: {elapsed:.2f}s")
```

---

## Migration from Old API

### Example 11: Gradual Migration

```python
from app.core.config import settings

def legacy_extract_text(image_bytes: bytes) -> str:
    """Legacy implementation (deprecated)"""
    # Old implementation with requests library
    pass

def new_extract_text(image_bytes: bytes) -> str:
    """New implementation with Interactions API"""
    from app.services.gemini_ocr import extract_text_with_gemini
    return extract_text_with_gemini(image_bytes)

def extract_text(image_bytes: bytes, use_legacy: bool = False) -> str:
    """Router function for gradual migration"""
    if use_legacy or settings.USE_LEGACY_API:
        return legacy_extract_text(image_bytes)
    else:
        return new_extract_text(image_bytes)

# Gradually migrate by setting USE_LEGACY_API=False in .env
```

---

## Configuration Examples

### Example 12: Different Configurations

```bash
# .env.development
GEMINI_API_KEY=sk_live_dev_key_here
GEMINI_MODEL=gemini-3-flash-preview
GEMINI_TIMEOUT=30

# .env.production
GEMINI_API_KEY=sk_live_prod_key_here
GEMINI_MODEL=gemini-3-pro-preview
GEMINI_TIMEOUT=60

# .env.testing
GEMINI_API_KEY=sk_test_key_here
GEMINI_MODEL=gemini-2.5-flash-lite
GEMINI_TIMEOUT=10
```

---

## Related Files

- [Gemini Interactions API Upgrade Guide](GEMINI_INTERACTIONS_API_UPGRADE.md)
- [Changes Summary](GEMINI_API_CHANGES_SUMMARY.md)
- [Source: gemini_ocr.py](app/services/gemini_ocr.py)
