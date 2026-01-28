import logging
from typing import Optional, cast
from PIL import Image  # type: ignore
import io
from transformers import TrOCRProcessor, VisionEncoderDecoderModel
import torch

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global variables for lazy loading the model
_processor: Optional[TrOCRProcessor] = None
_model: Optional[VisionEncoderDecoderModel] = None

class TrOCRError(Exception):
    pass

def _load_model():
    """
    Lazy load the TrOCR model to save memory if not used.
    Requires transformers and torch to be installed.
    """
    global _processor, _model
    if _processor is None or _model is None:
        try:
            logger.info("Loading TrOCR model (microsoft/trocr-base-handwritten)...")
            model_name = "microsoft/trocr-base-handwritten"
            _processor = TrOCRProcessor.from_pretrained(model_name)
            _model = VisionEncoderDecoderModel.from_pretrained(model_name)
            
            # Move to GPU if available
            if torch.cuda.is_available():
                _model = cast(VisionEncoderDecoderModel, _model.to("cuda"))  # type: ignore
                logger.info("TrOCR model moved to GPU.")
            else:
                logger.info("TrOCR model running on CPU.")
                
        except ImportError:
            logger.error("Transformers or Torch not installed. TrOCR unavailable.")
            raise TrOCRError("TrOCR dependencies (transformers, torch) not found.")
        except Exception as e:
            logger.error(f"Failed to load TrOCR model: {str(e)}")
            raise TrOCRError(f"TrOCR initialization failed: {str(e)}")

def extract_text_with_trocr(image_bytes: bytes) -> str:
    """
    Extract text from image using TrOCR (Priority 3).
    """
    global _processor, _model
    try:
        _load_model()
        import torch
        
        # Type assertions after load_model ensures types are not None
        assert _processor is not None, "Processor failed to load"
        assert _model is not None, "Model failed to load"
        
        image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        
        # Preprocess image
        pixel_values = _processor(images=image, return_tensors="pt").pixel_values  # type: ignore
        
        # Move input to same device as model
        device = next(_model.parameters()).device
        pixel_values = pixel_values.to(device)
        
        # Generate text
        logger.info("Generating text with TrOCR...")
        generated_ids = _model.generate(pixel_values)
        generated_text = _processor.batch_decode(generated_ids, skip_special_tokens=True)[0]
        
        logger.info(f"TrOCR extraction successful. Extracted {len(generated_text)} characters.")
        return generated_text.strip()
        
    except Exception as e:
        logger.error(f"TrOCR extraction failed: {str(e)}")
        raise TrOCRError(f"TrOCR failed: {str(e)}")