import logging
from typing import Optional, cast, TYPE_CHECKING
import io

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Type hints only - lazy imports for optional dependencies
if TYPE_CHECKING:
    from PIL import Image
    from transformers import TrOCRProcessor, VisionEncoderDecoderModel
    import torch
else:
    Image = None
    TrOCRProcessor = None
    VisionEncoderDecoderModel = None
    torch = None

# Global variables for lazy loading the model
_processor: Optional["TrOCRProcessor"] = None
_model: Optional["VisionEncoderDecoderModel"] = None

class TrOCRError(Exception):
    """Raised when TrOCR extraction fails"""
    pass


def _load_model():
    """
    Lazy load the TrOCR model to save memory if not used.
    Requires transformers, torch, and pillow to be installed.
    
    Raises:
        TrOCRError: When model loading fails or dependencies missing
    """
    global _processor, _model
    if _processor is None or _model is None:
        try:
            # Import only when actually needed
            from transformers import TrOCRProcessor, VisionEncoderDecoderModel
            import torch as torch_module
            
            logger.info("Loading TrOCR model (microsoft/trocr-base-handwritten)...")
            model_name = "microsoft/trocr-base-handwritten"
            _processor = TrOCRProcessor.from_pretrained(model_name)
            _model = VisionEncoderDecoderModel.from_pretrained(model_name)
            
            # Enhanced device selection and optimization
            device_name = "cuda" if torch_module.cuda.is_available() else "cpu"
            _model = _model.to(device_name)  # type: ignore
            
            # Enable optimizations
            _model.eval()
            if device_name == "cuda":
                torch_module.backends.cudnn.benchmark = True
                torch_module.cuda.empty_cache()
                logger.info(f"✅ TrOCR model loaded and optimized on GPU")
            else:
                logger.info("✅ TrOCR model loaded and optimized on CPU")
                
        except ImportError as e:
            logger.error(f"Missing dependencies for TrOCR: {str(e)}")
            raise TrOCRError(
                f"TrOCR dependencies not installed: {str(e)}\n"
                f"Please install optional dependencies: pip install transformers torch pillow\n"
                f"This is only required if you're using TrOCR as a fallback OCR provider."
            )
        except Exception as e:
            logger.error(f"Failed to load TrOCR model: {str(e)}", exc_info=True)
            raise TrOCRError(
                f"TrOCR model initialization failed: {str(e)}\n"
                f"This may be a network error (model download) or system resource issue."
            )


def extract_text_with_trocr(image_bytes: bytes) -> str:
    """
    Extract text from image using TrOCR (Transformer-based OCR - Tertiary Provider).
    
    This is a fallback OCR provider that requires no API keys and runs locally,
    but is slower than cloud-based providers.
    
    Args:
        image_bytes: Raw image bytes to extract text from
        
    Returns:
        Extracted text from the image
        
    Raises:
        TrOCRError: When extraction fails
    """
    global _processor, _model
    try:
        # Lazy import PIL only when actually needed
        try:
            from PIL import Image
        except ImportError:
            raise TrOCRError(
                "PIL (Pillow) not installed. Please install: pip install pillow\n"
                "This is only required if you're using TrOCR as a fallback OCR provider."
            )
        
        # Load model if not already loaded
        _load_model()
        import torch as torch_module
        
        # Type assertions after load_model ensures types are not None
        assert _processor is not None, "Processor failed to load"
        assert _model is not None, "Model failed to load"
        
        logger.debug("Loading image from bytes...")
        try:
            image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        except Exception as e:
            raise TrOCRError(f"Failed to load image: {str(e)}")
        
        # Preprocess image
        logger.debug("Preprocessing image...")
        try:
            pixel_values = _processor(images=image, return_tensors="pt").pixel_values  # type: ignore
        except Exception as e:
            raise TrOCRError(f"Image preprocessing failed: {str(e)}")
        
        # Move input to same device as model
        device = next(_model.parameters()).device
        pixel_values = pixel_values.to(device)
        
        # Generate text with timeout handling
        logger.info("Generating text with TrOCR (this may take a while on CPU)...")
        try:
            with torch_module.no_grad():
                generated_ids = _model.generate(pixel_values)
            generated_text = _processor.batch_decode(generated_ids, skip_special_tokens=True)[0]
        except Exception as e:
            raise TrOCRError(f"Text generation failed: {str(e)}")
        
        logger.info(f"✅ TrOCR extraction successful. Extracted {len(generated_text)} characters.")
        return generated_text.strip()
        
    except TrOCRError:
        # Re-raise TrOCRError as-is
        raise
    except Exception as e:
        logger.error(f"Unexpected error in TrOCR extraction: {str(e)}", exc_info=True)
        raise TrOCRError(f"TrOCR extraction failed: {str(e)}") from e